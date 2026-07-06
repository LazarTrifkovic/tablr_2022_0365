from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongo_url: str = "mongodb://barkds-db:27017/barkds"
    orders_url: str = "http://orders:8000"


settings = Settings()
