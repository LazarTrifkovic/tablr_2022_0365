from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongo_url: str = "mongodb://menu-db:27017/menu"
    # Frankfurter nema RSD; RSD→EUR ide preko ovog sidra, EUR→ostale preko Frankfurter-a.
    # Samo za PRIKAZ gostu (turisti); cene se čuvaju/naplaćuju u celim RSD.
    rsd_per_eur: float = 117.5


settings = Settings()
