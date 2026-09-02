"""Kafka consumer za barkds servis (Faza 4).

Umesto da čeka HTTP poziv od orders-a, barkds AKTIVNO SLUŠA `order-events` topic i
reaguje na događaje o porudžbini. Petlja radi ceo život aplikacije (pokreće se u
lifespan-u). Ako barkds padne pa se digne, Kafka (preko group offset-a) nastavlja
tačno odakle je stao — nijedan događaj se ne gubi niti duplira obradu.
"""
import asyncio
import json
import logging

from aiokafka import AIOKafkaConsumer

from app.config import settings
from app.routes import TicketIn, apply_new_ticket, apply_ticket_status

logger = logging.getLogger("barkds")

_task: asyncio.Task | None = None


STATUS_EVENT_TYPES = {"order.accepted", "order.ready", "order.delivered", "order.cancelled"}


async def _handle(event: dict) -> None:
    """Obrada jednog događaja. Isti posao kao stare HTTP interne rute, samo okinut
    porukom sa Kafke umesto zahtevom."""
    kind = event.get("type")
    if kind == "order.created":
        # event nosi tačno polja TicketIn-a (osim "type") — pydantic parsira
        body = TicketIn(**{k: v for k, v in event.items() if k != "type"})
        await apply_new_ticket(body)
    elif kind in STATUS_EVENT_TYPES:
        # order-status-changed nosi i tranzicije koje je POKRENUO sam barkds
        # (konobar → ticket-status-requests → orders validira → ovaj event) —
        # ažuriranje je idempotentno, samo prepisuje isti status ako je već primenjen.
        await apply_ticket_status(event["order_id"], event["status"])
    else:
        logger.info("Nepoznat tip događaja: %s (preskačem)", kind)


async def _run() -> None:
    consumer = AIOKafkaConsumer(
        settings.order_created_topic,
        settings.order_status_changed_topic,
        bootstrap_servers=settings.kafka_bootstrap,
        group_id=settings.kafka_group_id,
        value_deserializer=lambda b: json.loads(b.decode("utf-8")),
        auto_offset_reset="earliest",  # ako je grupa nova, čitaj od početka topica
        enable_auto_commit=True,
    )
    await consumer.start()
    logger.info("Kafka consumer sluša '%s' i '%s' (grupa %s)",
                settings.order_created_topic, settings.order_status_changed_topic,
                settings.kafka_group_id)
    try:
        async for msg in consumer:
            try:
                await _handle(msg.value)
            except Exception as exc:  # noqa: BLE001 — jedna loša poruka ne sme da obori petlju
                logger.exception("Greška pri obradi događaja: %s", exc)
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
