from pydantic_settings import BaseSettings


class APISettings(BaseSettings):
    database_url: str = "postgresql+asyncpg://deeplv:deeplv@localhost:5432/deeplv"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440
    model_worker_url: str = "http://localhost:8001"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "info"
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    model_config = {"env_file": ".env", "extra": "ignore"}


class WorkerSettings(BaseSettings):
    model_cache_size: int = 6
    model_dir: str = "/app/models"
    worker_host: str = "0.0.0.0"
    worker_port: int = 8001
    log_level: str = "info"

    model_config = {"env_file": ".env", "extra": "ignore"}
