from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    days_backward: int = 1
    max_transcript_len: int = 10000
    google_api_secret: str = "client_secret_yt.json"


config = Settings()
