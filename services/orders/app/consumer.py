"""Kafka consumer za orders servis (seminarski — hibridni Consumer+Producer modul).

orders KONZUMIRA zahteve za promenu statusa sa topica 'ticket-status-requests'
(objavljuje ih barkds kad konobar klikne dugme na dashboard-u), izvršava poslovnu
logiku (CAS tranzicija validirana kroz STATUS_FLOW — orders je vlasnik status
mašine), i PUBLIKUJE rezultat na 'order-status-changed' (isto što radi i
apply_status_transition za HTTP fallback put). Time se sinhroni HTTP poziv
barkds→orders iz Faze 4 zamenjuje asinhronim tokom preko Kafke.
"""
import asyncio
import json
import logging
import uuid

from aiokafka import AIOKafkaConsumer

from app.config import settings
from app.db import SessionLocal
from app.routes import apply_status_transition

logger = logging.getLogger("orders")

_task: asyncio.Task | None = None


async def _handle(event: dict) -> None:
    order_id = uuid.UUID(event["order_id"])
    status = event["status"]
    async with SessionLocal() as session:
        order, error = await apply_status_transition(
            order_id, status, event.get("taken_by"),
            event.get("payment_method"), session,
        )
    if error is not None:
        # nevalidna tranzicija ili trka sa konkurentnom promenom (npr. gost je
        # otkazao u međuvremenu) — zahtev se tiho odbacuje, isto ponašanje kao
        # 409 u sinhronom putu, samo bez klijenta koji čeka odgovor
        logger.info("Zahtev za status '%s' za porudžbinu %s odbijen: %s",
                    status, order_id, error)


async def _run() -> None:
    consumer = AIOKafkaConsumer(
        settings.ticket_status_requests_topic,
        bootstrap_servers=settings.kafka_bootstrap,
        group_id=settings.kafka_group_id,
        value_deserializer=lambda b: json.loads(b.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )
    await consumer.start()
    logger.info("Kafka consumer sluša '%s' (grupa %s)",
                settings.ticket_status_requests_topic, settings.kafka_group_id)
    try:
        async for msg in consumer:
            try:
                await _handle(msg.value)
            except Exception as exc:  # noqa: BLE001 — jedna loša poruka ne sme da obori petlju
                logger.exception("Greška pri obradi zahteva za status: %s", exc)
    finally:
        await consumer.stop()


async def start_consumer() -> None:
    global _task
    _task = asyncio.create_task(_run())


async def stop_consumer() -> None:
    global _task
    if _task is not None:
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
        _task = None
