from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    llm_base_url: str = "https://ai.bypc.com.cn/myopenai/v1"
    llm_chat_completions_url: str = "https://ai.bypc.com.cn/myopenai/v1/chat/completions"
    llm_api_key: str = ""
    llm_model: str = "zx/Qwen3.8-27B"
    parser_mode: str = "multimodal"
    ocr_url: str = "http://ocr:8090"
    upload_dir: str = "/data/uploads"
    max_pdf_pages: int = 3
    request_timeout_seconds: int = 120
    money_tolerance: float = 0.02
    cors_origins: str = "http://localhost:5173"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
