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
    
    # Cloud SQL Database settings
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "course_scheduler")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    
    # Cloud SQL specific settings
    CLOUD_SQL_CONNECTION_NAME: Optional[str] = os.getenv("CLOUD_SQL_CONNECTION_NAME", None)
    USE_CLOUD_SQL_PROXY: bool = os.getenv("USE_CLOUD_SQL_PROXY", "False").lower() == "true"
    
    # Database connection pool settings
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "10"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    
    # SSL settings for Cloud SQL
    DB_SSL_MODE: str = os.getenv("DB_SSL_MODE", "require")
    
    @property
    def database_url(self) -> str:
        """Construct database URL based on configuration"""
        if self.CLOUD_SQL_CONNECTION_NAME and not self.USE_CLOUD_SQL_PROXY:
            # Use Cloud SQL Connector for direct connection
            return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@/{self.DB_NAME}?host=/cloudsql/{self.CLOUD_SQL_CONNECTION_NAME}"
        else:
            # Standard connection (local development or Cloud SQL Proxy)
            return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
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