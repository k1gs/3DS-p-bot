from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    BOT_TOKEN: str
    RUTRACKER_USERNAME: str
    RUTRACKER_PASSWORD: str
    RUTRACKER_MIRROR: str = "https://rutracker.net"
    

    FORUM_ID: int = 774 # 3ds forum id
    
    CHECK_INTERVAL: int = 30 

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
