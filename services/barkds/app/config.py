from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongo_url: str = "mongodb://barkds-db:27017/barkds"
    orders_url: str = "http://orders:8000"
    qr_secret: str = "change-me"  # isti kao u orders — verifikacija QR potpisa stola
    # Kafka (Faza 4) — barkds KONZUMIRA događaje o porudžbini sa ovog topica
    kafka_bootstrap: str = "kafka:9092"
    order_events_topic: str = "order-events"
    kafka_group_id: str = "barkds"  # grupa čuva offset → nastavlja odakle je stao


settings = Settings()
