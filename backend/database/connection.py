from typing import Optional
from supabase import create_client, Client
from app.config import settings
from utils.logger import setup_logger
from utils.exceptions import DatabaseException

logger = setup_logger(__name__)


class DatabaseConnection:
    """Manages Supabase database connection"""
    
    _instance: Optional['DatabaseConnection'] = None
    _client: Optional[Client] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            self._initialize_connection()
    
    def _initialize_connection(self):
        """Initialize Supabase client connection"""
        try:
            if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
                raise DatabaseException("Supabase credentials not configured")
            
            self._client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            logger.info("Successfully connected to Supabase")
        except Exception as e:
            logger.error(f"Failed to connect to Supabase: {str(e)}")
            raise DatabaseException(f"Database connection failed: {str(e)}")
    
    @property
    def client(self) -> Client:
        """Get the Supabase client instance"""
        if self._client is None:
            self._initialize_connection()
        return self._client
    
    def get_table(self, table_name: str):
        """Get a specific table from the database"""
        return self.client.table(table_name)
    
    def close(self):
        """Close the database connection"""
        if self._client:
            self._client = None
            logger.info("Database connection closed")


# Singleton instance
db_connection = DatabaseConnection()