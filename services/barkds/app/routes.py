import logging
from datetime import datetime, timezone

import httpx
from beanie import PydanticObjectId
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.config import settings
from app.models import ServiceRequest, Ticket, TicketItem
from app.security import verify_table_signature
from app.ws import manager

logger = logging.getLogger("barkds")
router = APIRouter()

ACTIVE_STATUSES = ["CREATED", "ACCEPTED", "READY"]


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


def _ticket_dict(ticket: Ticket) -> dict:
    return {
        "order_id": ticket.order_id,
        "cafe_id": ticket.cafe_id,
        "table_number": ticket.table_number,
        "status": ticket.status,
        "note": ticket.note,
        "created_at": ticket.created_at.isoformat(),
        "items": [item.model_dump() for item in ticket.items],
    }


@router.post("/internal/tickets", status_code=201)
async def receive_ticket(body: TicketIn):
    """Prima novu porudžbinu od orders servisa. (U Fazi 4 postaje Kafka consumer.)"""
    existing = await Ticket.find_one(Ticket.order_id == body.order_id)
    if existing is not None:
        return _ticket_dict(existing)  # idempotentno — isti tiket ne dupliramo

    ticket = Ticket(**body.model_dump())
    await ticket.insert()
    await manager.broadcast(ticket.cafe_id,
                            {"type": "ticket.created", "ticket": _ticket_dict(ticket)})
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
    """Barmen menja status tiketa; promena se vraća u orders i emituje na WS."""
    ticket = await Ticket.find_one(Ticket.order_id == order_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # orders servis je vlasnik status mašine — on validira tranziciju
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.patch(
                f"{settings.orders_url}/internal/orders/{order_id}/status",
                json={"status": body.status},
            )
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="Orders service unavailable")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code,
                            detail=resp.json().get("detail", "Status update rejected"))

    ticket.status = body.status
    await ticket.save()
    await manager.broadcast(ticket.cafe_id,
                            {"type": "ticket.updated", "ticket": _ticket_dict(ticket)})
    return _ticket_dict(ticket)


class RequestIn(BaseModel):
    cafe_id: str
    table_number: int = Field(ge=1, le=500)
    sig: str
    kind: str  # "waiter" | "bill"


def _request_dict(req: ServiceRequest) -> dict:
    return {
        "id": str(req.id),
        "cafe_id": req.cafe_id,
        "table_number": req.table_number,
        "kind": req.kind,
        "status": req.status,
        "created_at": req.created_at.isoformat(),
    }


@router.post("/requests", status_code=201)
async def create_request(body: RequestIn):
    """Gost poziva konobara ili traži račun — potpis iz QR-a dokazuje sto."""
    if body.kind not in ("waiter", "bill"):
        raise HTTPException(status_code=400, detail="Unknown request kind")
    if not verify_table_signature(body.cafe_id, body.table_number, body.sig):
        raise HTTPException(status_code=403, detail="Invalid table signature")

    # anti-spam: isti sto + ista vrsta zahteva — vrati postojeći otvoren
    existing = await ServiceRequest.find_one(
        ServiceRequest.cafe_id == body.cafe_id,
        ServiceRequest.table_number == body.table_number,
        ServiceRequest.kind == body.kind,
        ServiceRequest.status == "OPEN",
    )
    if existing is not None:
        return _request_dict(existing)

    req = ServiceRequest(cafe_id=body.cafe_id, table_number=body.table_number,
                         kind=body.kind, created_at=datetime.now(timezone.utc))
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
