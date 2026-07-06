import logging
from datetime import datetime

import httpx
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.config import settings
from app.models import Ticket, TicketItem
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


@router.websocket("/ws/{cafe_id}")
async def ws_endpoint(ws: WebSocket, cafe_id: str):
    await manager.connect(cafe_id, ws)
    try:
        while True:
            await ws.receive_text()  # dashboard ne šalje ništa; držimo konekciju
    except WebSocketDisconnect:
        await manager.disconnect(cafe_id, ws)
