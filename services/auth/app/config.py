from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://auth:auth@auth-db:5432/auth"
    menu_url: str = "http://menu:8000"  # za seed: veže demo naloge na demo kafić
    # tajni ključ za potpis JWT-a — ISTI mora imati gateway (on validira token)
    jwt_secret: str = "dev-jwt-secret-change-in-prod"
    jwt_ttl_hours: int = 12  # trajanje smene
    app_env: str = "dev"


settings = Settings()
