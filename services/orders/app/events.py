"""Kafka producer za orders servis (Faza 4).

Umesto direktnog HTTP poziva ka barkds-u, orders OBJAVLJUJE događaje o životnom
ciklusu porudžbine na `order-events` topic. Ko sluša (barkds) — nije briga orders-a.
Ovim se sinhrona zavisnost orders→barkds pretvara u asinhronu (decoupling + otpornost:
ako je barkds pao, događaj čeka u Kafki i obradi se po oporavku).
"""
import json
import logging

from aiokafka import AIOKafkaProducer

from app.config import settings

logger = logging.getLogger("orders")

_producer: AIOKafkaProducer | None = None


async def start_producer() -> None:
    global _producer
    _producer = AIOKafkaProducer(bootstrap_servers=settings.kafka_bootstrap)
    await _producer.start()
    logger.info("Kafka producer povezan na %s", settings.kafka_bootstrap)


async def stop_producer() -> None:
    global _producer
    if _producer is not None:
        await _producer.stop()
        _producer = None


async def publish_order_event(event: dict) -> None:
    """Objavi događaj na order-events topic. Porudžbina je već sačuvana u bazi pre
    ovog poziva, pa ako Kafka trenutno ne radi — logujemo i ne rušimo zahtev gosta
    (best-effort; trajno rešenje 'outbox' je kandidat za kasnije)."""
    if _producer is None:
        logger.warning("Kafka producer nije spreman — događaj %s preskočen",
                       event.get("type"))
        return
    try:
        payload = json.dumps(event).encode("utf-8")
        # send_and_wait čeka potvrdu BROKERA (ne barkds-a) da je poruka trajno primljena
        await _producer.send_and_wait(settings.order_events_topic, payload)
    except Exception as exc:  # noqa: BLE001 — Kafka nedostupna ne sme da obori porudžbinu
        logger.warning("Objava događaja %s nije uspela: %s", event.get("type"), exc)
