from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongo_url: str = "mongodb://menu-db:27017/menu"
    # Frankfurter nema RSD; RSD→EUR ide preko ovog sidra, EUR→ostale preko Frankfurter-a.
    # Samo za PRIKAZ gostu (turisti); cene se čuvaju/naplaćuju u celim RSD.
    rsd_per_eur: float = 117.5
    # isti tajni ključ kao orders/barkds — za generisanje QR potpisa stolova (admin)
    qr_secret: str = "change-me"
    # bazna adresa gost aplikacije (u QR link se ugrađuje cafe/table/sig)
    guest_base_url: str = "http://localhost:5173"


settings = Settings()
