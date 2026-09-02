"""Kafka producer za barkds servis (seminarski — hibridni Consumer+Producer modul).

barkds KONZUMIRA sa 'order-created'/'order-status-changed' (v. app/consumer.py) i
OVDE PUBLIKUJE na 'ticket-status-requests' kad konobar sa dashboard-a promeni
status tiketa — zamenjuje sinhroni HTTP poziv ka orders-u iz Faze 4.
"""
import json
import logging

from aiokafka import AIOKafkaProducer

from app.config import settings

logger = logging.getLogger("barkds")

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


async def publish_ticket_status_request(event: dict) -> None:
    """Objavi zahtev za promenu statusa na 'ticket-status-requests'. Tiket je već
    optimistički ažuriran lokalno (v. routes.py) pre ovog poziva, pa ako Kafka
    trenutno ne radi — logujemo i ne rušimo zahtev konobara (best-effort)."""
    if _producer is None:
        logger.warning("Kafka producer nije spreman — zahtev za status %s preskočen",
                       event.get("status"))
        return
    try:
        payload = json.dumps(event).encode("utf-8")
        await _producer.send_and_wait(settings.ticket_status_requests_topic, payload)
    except Exception as exc:  # noqa: BLE001 — Kafka nedostupna ne sme da obori zahtev
        logger.warning("Objava zahteva za status nije uspela: %s", exc)
