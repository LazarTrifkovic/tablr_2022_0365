import logging
from datetime import datetime, timezone

from beanie import PydanticObjectId
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.config import settings
from app.events import publish_ticket_status_request
from app.models import ServiceRequest, Ticket, TicketItem
from app.security import verify_table_signature
from app.ws import manager

logger = logging.getLogger("barkds")
router = APIRouter()

ACTIVE_STATUSES = ["CREATED", "ACCEPTED", "READY"]

# Ogledalo orders/app/models.py STATUS_FLOW — orders OSTAJE jedini vlasnik
# konačne validacije (CAS u bazi), ali barkds ovim brzo odbija OČIGLEDNO
# nevalidnu tranziciju bez čekanja na Kafka povratni krug (npr. ACCEPTED
# direktno u DELIVERED, preskačući READY).
STATUS_FLOW: dict[str, set[str]] = {
    "CREATED": {"ACCEPTED", "CANCELLED"},
    "ACCEPTED": {"READY", "CANCELLED"},
    "READY": {"DELIVERED"},
    "DELIVERED": set(),
    "CANCELLED": set(),
}


def _iso_utc(dt: datetime) -> str:
    """ISO string sa UTC oznakom. Mongo vraća naive datetime (bez tz), pa bez ovoga
    frontend čita vreme kao lokalno i tajmer 'skoči' za offset (npr. +2h leti)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


class TicketIn(BaseModel):
    order_id: str
    cafe_id: str
    table_number: int
    status: str = "CREATED"
    note: str | None = None
    created_at: datetime
    items: list[TicketItem]


class StatusUpdate(BaseModel):
    status: str
    payment_method: str | None = None  # konobar označi keš/kartica pri isporuci


def _ticket_dict(ticket: Ticket) -> dict:
    return {
        "order_id": ticket.order_id,
        "cafe_id": ticket.cafe_id,
        "table_number": ticket.table_number,
        "status": ticket.status,
        "note": ticket.note,
        "created_at": _iso_utc(ticket.created_at),
        "items": [item.model_dump() for item in ticket.items],
    }


# --- Zajednička logika: koriste je I Kafka consumer (app/consumer.py) I HTTP rute ispod.
# Time se isti posao (upis tiketa + WS broadcast) ne duplira. ---

async def apply_new_ticket(body: TicketIn) -> Ticket:
    """Kreira tiket iz porudžbine i emituje ga baru. Idempotentno — ako tiket za taj
    order_id već postoji (npr. Kafka isporuči poruku dvaput), vraća postojeći."""
    existing = await Ticket.find_one(Ticket.order_id == body.order_id)
    if existing is not None:
        return existing
    ticket = Ticket(**body.model_dump())
    await ticket.insert()
    await manager.broadcast(ticket.cafe_id,
                            {"type": "ticket.created", "ticket": _ticket_dict(ticket)})
    return ticket


async def apply_ticket_status(order_id: str, status: str) -> Ticket | None:
    """Menja status postojećeg tiketa i emituje `ticket.updated`. Vraća None ako
    tiket ne postoji (npr. otkazivanje pre nego što je tiket uopšte stigao).
    Ako je status VEĆ isti (npr. potvrda sa Kafke stigne posle optimističkog
    lokalnog upisa u update_status ispod) — preskače upis i emitovanje, da se
    isti prelaz ne prikaže baru dvaput."""
    ticket = await Ticket.find_one(Ticket.order_id == order_id)
    if ticket is None:
        return None
    if ticket.status == status:
        return ticket
    ticket.status = status
    await ticket.save()
    await manager.broadcast(ticket.cafe_id,
                            {"type": "ticket.updated", "ticket": _ticket_dict(ticket)})
    return ticket


@router.post("/internal/tickets", status_code=201)
async def receive_ticket(body: TicketIn):
    """HTTP fallback za prijem tiketa (primarni put je Kafka consumer). Ostaje kao
    rezervni/interni ulaz; blokiran na gateway-u spolja."""
    return _ticket_dict(await apply_new_ticket(body))


@router.patch("/internal/tickets/{order_id}/status")
async def receive_status(order_id: str, body: StatusUpdate):
    """HTTP fallback za promenu statusa iz orders-a (primarni put je Kafka consumer)."""
    ticket = await apply_ticket_status(order_id, body.status)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return _ticket_dict(ticket)


@router.get("/tickets")
async def list_tickets(cafe_id: str, active: bool = True):
    """Tiketi kafića — inicijalno punjenje bar dashboard-a."""
    query = Ticket.find(Ticket.cafe_id == cafe_id)
    if active:
        query = query.find({"status": {"$in": ACTIVE_STATUSES}})
    tickets = await query.sort("+created_at").to_list()
    return [_ticket_dict(t) for t in tickets]


@router.patch("/tickets/{order_id}/status")
async def update_status(order_id: str, body: StatusUpdate):
    """Barmen menja status tiketa. Ranije: sinhroni HTTP poziv ka orders-u koji
    čeka potvrdu (Faza 4). Sad: tiket se ažurira OPTIMISTIČKI odmah (isti WS
    ugovor za bar dashboard — frontend ne zna razliku), a zahtev se ASINHRONO
    šalje na 'ticket-status-requests'; orders (vlasnik status mašine) ga
    konzumira, validira i objavljuje autoritativan rezultat na
    'order-status-changed', koji naš consumer (app/consumer.py) prima i ponovo
    upisuje — zatvara petlju bez čekanja. Kompromis: nevalidna tranzicija se
    tiho odbaci na orders strani bez eksplicitne ispravke ka baru (redak slučaj,
    UI već nudi samo validne prelaze pa se praktično ne dešava)."""
    ticket = await Ticket.find_one(Ticket.order_id == order_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if body.status not in STATUS_FLOW.get(ticket.status, set()):
        raise HTTPException(status_code=409,
                            detail=f"Invalid transition {ticket.status} -> {body.status}")

    ticket.status = body.status
    await ticket.save()
    await manager.broadcast(ticket.cafe_id,
                            {"type": "ticket.updated", "ticket": _ticket_dict(ticket)})

    event: dict = {"order_id": order_id, "status": body.status}
    if body.payment_method:
        event["payment_method"] = body.payment_method
    await publish_ticket_status_request(event)

    return _ticket_dict(ticket)


class RequestIn(BaseModel):
    cafe_id: str
    table_number: int = Field(ge=1, le=500)
    sig: str
    kind: str  # "waiter" | "bill" | "bill_split"
    detail: str | None = None
    item_ids: list[int] | None = None
    amount: int | None = None


def _request_dict(req: ServiceRequest) -> dict:
    return {
        "id": str(req.id),
        "cafe_id": req.cafe_id,
        "table_number": req.table_number,
        "kind": req.kind,
        "status": req.status,
        "created_at": _iso_utc(req.created_at),
        "detail": req.detail,
        "item_ids": req.item_ids,
        "amount": req.amount,
    }


@router.post("/requests", status_code=201)
async def create_request(body: RequestIn):
    """Gost poziva konobara, traži račun ili naplatu izabranih stavki — potpis dokazuje sto."""
    if body.kind not in ("waiter", "bill", "bill_split"):
        raise HTTPException(status_code=400, detail="Unknown request kind")
    if not verify_table_signature(body.cafe_id, body.table_number, body.sig):
        raise HTTPException(status_code=403, detail="Invalid table signature")

    # anti-spam: isti sto + ista vrsta — vrati postojeći otvoren.
    # bill_split je izuzet: svaki nosi različit skup stavki, ne sme se spajati.
    if body.kind != "bill_split":
        existing = await ServiceRequest.find_one(
            ServiceRequest.cafe_id == body.cafe_id,
            ServiceRequest.table_number == body.table_number,
            ServiceRequest.kind == body.kind,
            ServiceRequest.status == "OPEN",
        )
        if existing is not None:
            return _request_dict(existing)

    req = ServiceRequest(cafe_id=body.cafe_id, table_number=body.table_number,
                         kind=body.kind, created_at=datetime.now(timezone.utc),
                         detail=body.detail, item_ids=body.item_ids, amount=body.amount)
    await req.insert()
    await manager.broadcast(req.cafe_id,
                            {"type": "request.created", "request": _request_dict(req)})
    return _request_dict(req)


@router.get("/requests")
async def list_requests(cafe_id: str, open: bool = True):
    query = ServiceRequest.find(ServiceRequest.cafe_id == cafe_id)
    if open:
        query = query.find(ServiceRequest.status == "OPEN")
    requests = await query.sort("+created_at").to_list()
    return [_request_dict(r) for r in requests]


@router.patch("/requests/{request_id}/resolve")
async def resolve_request(request_id: str):
    try:
        req = await ServiceRequest.get(PydanticObjectId(request_id))
    except Exception:
        req = None
    if req is None:
        raise HTTPException(status_code=404, detail="Request not found")
    req.status = "RESOLVED"
    await req.save()
    await manager.broadcast(req.cafe_id,
                            {"type": "request.resolved", "request": _request_dict(req)})
    return _request_dict(req)


@router.websocket("/ws/{cafe_id}")
async def ws_endpoint(ws: WebSocket, cafe_id: str):
    await manager.connect(cafe_id, ws)
    try:
        while True:
            await ws.receive_text()  # dashboard ne šalje ništa; držimo konekciju
    except WebSocketDisconnect:
        await manager.disconnect(cafe_id, ws)
