from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./quantlab.db"
    cors_origins: str = "http://localhost:3000,http://localhost:4173"
    helius_api_key: str = ""
    birdeye_api_key: str = ""
    seed_demo: bool = True
    max_concurrent_jobs: int = 2
    api_token: str = ""  # Optional local/reverse-proxy bearer token; never exposed to browser builds.


settings = Settings()
