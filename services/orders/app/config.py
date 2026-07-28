from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://orders:orders@orders-db:5432/orders"
    menu_url: str = "http://menu:8000"
    barkds_url: str = "http://barkds:8000"
    qr_secret: str = "change-me"
    app_env: str = "dev"  # u "dev" režimu postoji /dev/sign pomoćna ruta
    # Kafka (Faza 4) — orders OBJAVLJUJE događaje o porudžbini na ovaj topic
    kafka_bootstrap: str = "kafka:9092"
    order_events_topic: str = "order-events"


settings = Settings()
