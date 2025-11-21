from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str
    admin_id: int

    database_user: str
    database_password: str
    database_host: str
    database_port: int
    database_name: str

    xui_url_panel: str
    xui_url_subscriptions: str
    xui_username: str
    xui_password: str

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.database_user}:{self.database_password}@{self.database_host}:{self.database_port}/{self.database_name}"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
