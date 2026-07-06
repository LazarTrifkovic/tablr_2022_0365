from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://orders:orders@orders-db:5432/orders"
    menu_url: str = "http://menu:8000"
    barkds_url: str = "http://barkds:8000"
    qr_secret: str = "change-me"
    app_env: str = "dev"  # u "dev" režimu postoji /dev/sign pomoćna ruta


settings = Settings()
