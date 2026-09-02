from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongo_url: str = "mongodb://barkds-db:27017/barkds"
    orders_url: str = "http://orders:8000"
    qr_secret: str = "change-me"  # isti kao u orders — verifikacija QR potpisa stola
    # Kafka (seminarski) — barkds je HIBRIDNI modul: KONZUMIRA sa 2 teme (nova
    # porudžbina, promena statusa) i OBJAVLJUJE na treću (zahtev za promenu
    # statusa koji šalje konobar sa dashboard-a — orders je konzumira i validira).
    kafka_bootstrap: str = "kafka:9092"
    order_created_topic: str = "order-created"
    order_status_changed_topic: str = "order-status-changed"
    ticket_status_requests_topic: str = "ticket-status-requests"
    kafka_group_id: str = "barkds"  # grupa čuva offset → nastavlja odakle je stao


settings = Settings()
