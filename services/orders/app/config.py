from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://orders:orders@orders-db:5432/orders"
    menu_url: str = "http://menu:8000"
    barkds_url: str = "http://barkds:8000"
    qr_secret: str = "change-me"
    app_env: str = "dev"  # u "dev" režimu postoji /dev/sign pomoćna ruta
    # Kafka (seminarski) — orders je HIBRIDNI modul: OBJAVLJUJE na 3 teme i
    # KONZUMIRA sa jedne (zahtevi za promenu statusa od bara).
    kafka_bootstrap: str = "kafka:9092"
    order_created_topic: str = "order-created"
    order_status_changed_topic: str = "order-status-changed"
    order_rated_topic: str = "order-rated"
    ticket_status_requests_topic: str = "ticket-status-requests"
    kafka_group_id: str = "orders"


settings = Settings()
