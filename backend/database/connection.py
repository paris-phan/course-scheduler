from typing import Optional, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from google.cloud.sql.connector import Connector
import asyncpg
from app.config import settings
from utils.logger import setup_logger
from utils.exceptions import DatabaseException

logger = setup_logger(__name__)


class DatabaseConnection:
    """Manages SQLAlchemy database connection for Google Cloud SQL"""
    
    _instance: Optional['DatabaseConnection'] = None
    _engine = None
    _session_factory = None
    _connector: Optional[Connector] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._engine is None:
            self._initialize_connection()
    
    def _initialize_connection(self):
        """Initialize SQLAlchemy async engine and session factory"""
        try:
            if settings.CLOUD_SQL_CONNECTION_NAME and not settings.USE_CLOUD_SQL_PROXY:
                # Use Cloud SQL Connector for direct connection
                self._setup_cloud_sql_connector()
            else:
                # Standard connection (local development or Cloud SQL Proxy)
                self._setup_standard_connection()
            
            # Create session factory
            self._session_factory = async_sessionmaker(
                bind=self._engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            logger.info("Successfully initialized database connection")
            
        except Exception as e:
            logger.error(f"Failed to initialize database connection: {str(e)}")
            raise DatabaseException(f"Database connection failed: {str(e)}")
    
    def _setup_cloud_sql_connector(self):
        """Setup Cloud SQL Connector for direct connection"""
        from google.cloud.sql.connector import Connector
        
        async def getconn() -> asyncpg.Connection:
            if self._connector is None:
                self._connector = Connector()
            
            conn: asyncpg.Connection = await self._connector.connect_async(
                settings.CLOUD_SQL_CONNECTION_NAME,
                "asyncpg",
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                db=settings.DB_NAME,
            )
            return conn
        
        # Create engine with Cloud SQL Connector
        self._engine = create_async_engine(
            "postgresql+asyncpg://",
            async_creator=getconn,
            poolclass=NullPool,
            echo=settings.DEBUG,
        )
        
        logger.info("Using Cloud SQL Connector for database connection")
    
    def _setup_standard_connection(self):
        """Setup standard connection (local development or Cloud SQL Proxy)"""
        database_url = settings.database_url
        
        # Create engine with connection pooling
        self._engine = create_async_engine(
            database_url,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_timeout=settings.DB_POOL_TIMEOUT,
            echo=settings.DEBUG,
            # SSL configuration for Cloud SQL
            connect_args={
                "server_settings": {
                    "application_name": settings.APP_NAME,
                }
            } if not settings.DEBUG else {}
        )
        
        logger.info(f"Using standard connection: {database_url.split('@')[0]}@***")
    
    @property
    def engine(self):
        """Get the SQLAlchemy async engine"""
        if self._engine is None:
            self._initialize_connection()
        return self._engine
    
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get an async database session"""
        if self._session_factory is None:
            self._initialize_connection()
        
        async with self._session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def create_tables(self):
        """Create all tables in the database"""
        from database.models import Base
        
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database tables created successfully")
    
    async def drop_tables(self):
        """Drop all tables in the database"""
        from database.models import Base
        
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        
        logger.info("Database tables dropped successfully")
    
    async def close(self):
        """Close the database connection"""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
        
        if self._connector:
            await self._connector.close_async()
            self._connector = None
        
        logger.info("Database connection closed")


# Singleton instance
db_connection = DatabaseConnection()


# Dependency for FastAPI
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency to get database session"""
    async for session in db_connection.get_session():
        yield session