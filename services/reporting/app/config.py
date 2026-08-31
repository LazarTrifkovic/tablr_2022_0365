from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongo_url: str = "mongodb://reporting-db:27017/reporting"
    # Kafka (Faza 4 / CQRS) — reporting je READ strana: samo konzumira događaje
    kafka_bootstrap: str = "kafka:9092"
    order_events_topic: str = "order-events"
    kafka_group_id: str = "reporting"  # svoja grupa → svoj offset, nezavisno od barkds-a


settings = Settings()
