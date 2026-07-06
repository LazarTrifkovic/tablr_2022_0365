from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongo_url: str = "mongodb://menu-db:27017/menu"


settings = Settings()
