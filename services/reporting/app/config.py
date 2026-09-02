from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongo_url: str = "mongodb://reporting-db:27017/reporting"
    # Kafka (CQRS) — reporting je READ strana: samo konzumira događaje, sa dve teme
    # (status promene radi order.delivered, i ocene radi order.rated)
    kafka_bootstrap: str = "kafka:9092"
    order_status_changed_topic: str = "order-status-changed"
    order_rated_topic: str = "order-rated"
    kafka_group_id: str = "reporting"  # svoja grupa → svoj offset, nezavisno od barkds-a


settings = Settings()
