"""Projektor (CQRS read strana) — gradi/održava read model iz događaja o porudžbini.

Sluša `order-events` i na `order.delivered`/`order.rated` inkrementalno ažurira agregat
po kafiću (CafeStats). Ne dira orders (write) bazu. Pošto je jedan consumer koji obrađuje
poruke redom, čitaj-izmeni-upiši nad CafeStats je bezbedno; dedup (ProcessedEvent) štiti
od duplog brojanja pri Kafka redelivery-ju.
"""
import asyncio
import json
import logging

from aiokafka import AIOKafkaConsumer
from pymongo.errors import DuplicateKeyError

from app.config import settings
from app.models import CafeStats, ProcessedEvent

logger = logging.getLogger("reporting")

_task: asyncio.Task | None = None


async def _already_processed(key: str) -> bool:
    """True ako je događaj već obrađen (idempotentnost). Inače ga zabeleži i vrati False."""
    try:
        await ProcessedEvent(key=key).insert()
        return False
    except DuplicateKeyError:
        return True


async def _stats(cafe_id: str) -> CafeStats:
    stats = await CafeStats.find_one(CafeStats.cafe_id == cafe_id)
    if stats is None:
        stats = CafeStats(cafe_id=cafe_id)
        await stats.insert()
    return stats


async def _handle(event: dict) -> None:
    kind = event.get("type")
    if kind == "order.delivered":
        if await _already_processed(f"{event['order_id']}:delivered"):
            return
        stats = await _stats(event["cafe_id"])
        stats.orders_count += 1
        stats.revenue += int(event.get("total", 0))
        prep = event.get("prep_seconds")
        if prep is not None:
            stats.prep_seconds_sum += int(prep)
            stats.prep_seconds_count += 1
        pm = event.get("payment_method")
        if pm == "cash":
            stats.cash_count += 1
        elif pm == "card":
            stats.card_count += 1
        await stats.save()
    elif kind == "order.rated":
        if await _already_processed(f"{event['order_id']}:rated"):
            return
        stats = await _stats(event["cafe_id"])
        stats.rating_sum += int(event["rating"])
        stats.rating_count += 1
        await stats.save()
    # order.created / order.cancelled — reporting ih ignoriše (nije njegova briga)


async def _run() -> None:
    consumer = AIOKafkaConsumer(
        settings.order_status_changed_topic,
        settings.order_rated_topic,
        bootstrap_servers=settings.kafka_bootstrap,
        group_id=settings.kafka_group_id,
        value_deserializer=lambda b: json.loads(b.decode("utf-8")),
        auto_offset_reset="earliest",  # nov read model se gradi od početka event loga
        enable_auto_commit=True,
    )
    await consumer.start()
    logger.info("Projektor sluša '%s' i '%s' (grupa %s)",
                settings.order_status_changed_topic, settings.order_rated_topic,
                settings.kafka_group_id)
    try:
        async for msg in consumer:
            try:
                await _handle(msg.value)
            except Exception as exc:  # noqa: BLE001 — jedna loša poruka ne ruši projektor
                logger.exception("Greška u projekciji: %s", exc)
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
