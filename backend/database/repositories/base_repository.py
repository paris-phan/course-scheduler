from typing import TypeVar, Generic, List, Optional, Dict, Any, Type
from abc import ABC, abstractmethod
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import selectinload
from database.connection import get_db_session
from utils.logger import setup_logger
from utils.exceptions import DatabaseException

T = TypeVar('T')
logger = setup_logger(__name__)


class BaseRepository(ABC, Generic[T]):
    """Base repository class with common SQLAlchemy operations"""
    
    def __init__(self, model_class: Type[T]):
        self.model_class = model_class
    
    async def find_all(
        self, 
        session: AsyncSession, 
        limit: Optional[int] = None, 
        offset: Optional[int] = None,
        load_relationships: List[str] = None
    ) -> List[T]:
        """Retrieve all records with optional pagination and relationships"""
        try:
            query = select(self.model_class)
            
            # Load relationships if specified
            if load_relationships:
                for rel in load_relationships:
                    query = query.options(selectinload(getattr(self.model_class, rel)))
            
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            
            result = await session.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error retrieving records from {self.model_class.__tablename__}: {str(e)}")
            raise DatabaseException(f"Failed to retrieve records: {str(e)}")
    
    async def find_by_id(
        self, 
        session: AsyncSession, 
        record_id: Any,
        load_relationships: List[str] = None
    ) -> Optional[T]:
        """Find a record by ID"""
        try:
            query = select(self.model_class).where(self.model_class.id == record_id)
            
            # Load relationships if specified
            if load_relationships:
                for rel in load_relationships:
                    query = query.options(selectinload(getattr(self.model_class, rel)))
            
            result = await session.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error finding record by ID in {self.model_class.__tablename__}: {str(e)}")
            raise DatabaseException(f"Failed to find record: {str(e)}")
    
    async def create(self, session: AsyncSession, **kwargs) -> T:
        """Create a new record"""
        try:
            entity = self.model_class(**kwargs)
            session.add(entity)
            await session.commit()
            await session.refresh(entity)
            return entity
        except Exception as e:
            await session.rollback()
            logger.error(f"Error creating record in {self.model_class.__tablename__}: {str(e)}")
            raise DatabaseException(f"Failed to create record: {str(e)}")
    
    async def create_many(self, session: AsyncSession, entities_data: List[Dict[str, Any]]) -> List[T]:
        """Create multiple records"""
        try:
            entities = [self.model_class(**data) for data in entities_data]
            session.add_all(entities)
            await session.commit()
            
            # Refresh all entities to get their IDs
            for entity in entities:
                await session.refresh(entity)
            
            return entities
        except Exception as e:
            await session.rollback()
            logger.error(f"Error creating multiple records in {self.model_class.__tablename__}: {str(e)}")
            raise DatabaseException(f"Failed to create records: {str(e)}")
    
    async def update(self, session: AsyncSession, record_id: Any, **kwargs) -> Optional[T]:
        """Update a record by ID"""
        try:
            # Remove None values to avoid updating with null
            update_data = {k: v for k, v in kwargs.items() if v is not None}
            
            if not update_data:
                # If no data to update, just return the existing record
                return await self.find_by_id(session, record_id)
            
            stmt = (
                update(self.model_class)
                .where(self.model_class.id == record_id)
                .values(**update_data)
                .returning(self.model_class)
            )
            
            result = await session.execute(stmt)
            await session.commit()
            
            updated_record = result.scalar_one_or_none()
            if updated_record:
                await session.refresh(updated_record)
            return updated_record
        except Exception as e:
            await session.rollback()
            logger.error(f"Error updating record in {self.model_class.__tablename__}: {str(e)}")
            raise DatabaseException(f"Failed to update record: {str(e)}")
    
    async def delete(self, session: AsyncSession, record_id: Any) -> bool:
        """Delete a record by ID"""
        try:
            stmt = delete(self.model_class).where(self.model_class.id == record_id)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0
        except Exception as e:
            await session.rollback()
            logger.error(f"Error deleting record from {self.model_class.__tablename__}: {str(e)}")
            raise DatabaseException(f"Failed to delete record: {str(e)}")
    
    async def exists(self, session: AsyncSession, record_id: Any) -> bool:
        """Check if a record exists by ID"""
        try:
            query = select(func.count()).select_from(
                select(self.model_class.id).where(self.model_class.id == record_id).subquery()
            )
            result = await session.execute(query)
            count = result.scalar()
            return count > 0
        except Exception as e:
            logger.error(f"Error checking record existence in {self.model_class.__tablename__}: {str(e)}")
            raise DatabaseException(f"Failed to check record existence: {str(e)}")
    
    async def find_by_field(
        self, 
        session: AsyncSession, 
        field_name: str, 
        value: Any,
        limit: Optional[int] = None
    ) -> List[T]:
        """Find records by a specific field value"""
        try:
            field = getattr(self.model_class, field_name)
            query = select(self.model_class).where(field == value)
            
            if limit:
                query = query.limit(limit)
            
            result = await session.execute(query)
            return result.scalars().all()
        except AttributeError:
            raise DatabaseException(f"Field '{field_name}' not found in {self.model_class.__name__}")
        except Exception as e:
            logger.error(f"Error finding records by field in {self.model_class.__tablename__}: {str(e)}")
            raise DatabaseException(f"Failed to find records: {str(e)}")
    
    async def find_by_fields(
        self, 
        session: AsyncSession, 
        filters: Dict[str, Any],
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[T]:
        """Find records by multiple field values"""
        try:
            query = select(self.model_class)
            
            # Apply filters
            for field_name, value in filters.items():
                if hasattr(self.model_class, field_name):
                    field = getattr(self.model_class, field_name)
                    if isinstance(value, list):
                        query = query.where(field.in_(value))
                    else:
                        query = query.where(field == value)
                else:
                    raise DatabaseException(f"Field '{field_name}' not found in {self.model_class.__name__}")
            
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            
            result = await session.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error finding records by fields in {self.model_class.__tablename__}: {str(e)}")
            raise DatabaseException(f"Failed to find records: {str(e)}")
    
    async def count(
        self, 
        session: AsyncSession, 
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """Count records with optional filters"""
        try:
            query = select(func.count()).select_from(self.model_class)
            
            if filters:
                for field_name, value in filters.items():
                    if hasattr(self.model_class, field_name):
                        field = getattr(self.model_class, field_name)
                        if isinstance(value, list):
                            query = query.where(field.in_(value))
                        else:
                            query = query.where(field == value)
            
            result = await session.execute(query)
            return result.scalar()
        except Exception as e:
            logger.error(f"Error counting records in {self.model_class.__tablename__}: {str(e)}")
            raise DatabaseException(f"Failed to count records: {str(e)}")