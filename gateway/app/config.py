from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    menu_url: str = "http://menu:8000"
    orders_url: str = "http://orders:8000"
    barkds_url: str = "http://barkds:8000"
    auth_url: str = "http://auth:8000"
    payments_url: str = "http://payments:8000"
    # isti tajni ključ kao auth servis — gateway validira JWT osoblja
    jwt_secret: str = "dev-jwt-secret-change-in-prod"
    # zarezom razdvojene dozvoljene CORS origin adrese (frontend aplikacije)
    cors_origins: str = "http://localhost:5173,http://localhost:5174,http://localhost:5175"


settings = Settings()
