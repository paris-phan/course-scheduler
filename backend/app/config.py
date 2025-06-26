import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # App settings
    APP_NAME: str = "Course Scheduler API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # API settings
    API_V1_STR: str = "/api/v1"
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # Database settings
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    
    # UVA SIS API settings
    UVA_API_BASE_URL: str = "https://sisuva.admin.virginia.edu/psc/ihprd/UVSS/SA/s/WEBLIB_HCX_CM.H_CLASS_SEARCH.FieldFormula.IScript_ClassSearch"
    UVA_API_TERM: str = os.getenv("UVA_API_TERM", "1258")  # Fall 2025
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # CORS settings
    BACKEND_CORS_ORIGINS: list[str] = os.getenv(
        "BACKEND_CORS_ORIGINS", "http://localhost:3000,http://localhost:8000"
    ).split(",")
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()