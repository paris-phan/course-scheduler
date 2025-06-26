from typing import TypeVar, Generic, List, Optional, Dict, Any
from abc import ABC, abstractmethod
from database.connection import db_connection
from utils.logger import setup_logger
from utils.exceptions import DatabaseException

T = TypeVar('T')
logger = setup_logger(__name__)


class BaseRepository(ABC, Generic[T]):
    """Base repository class with common database operations"""
    
    def __init__(self, table_name: str):
        self.table_name = table_name
        self.db = db_connection
    
    @abstractmethod
    def to_entity(self, data: Dict[str, Any]) -> T:
        """Convert database row to entity"""
        pass
    
    @abstractmethod
    def to_dict(self, entity: T) -> Dict[str, Any]:
        """Convert entity to dictionary for database operations"""
        pass
    
    def find_all(self, limit: Optional[int] = None, offset: Optional[int] = None) -> List[T]:
        """Retrieve all records with optional pagination"""
        try:
            query = self.db.get_table(self.table_name).select("*")
            
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)
            
            response = query.execute()
            return [self.to_entity(row) for row in response.data]
        except Exception as e:
            logger.error(f"Error retrieving records from {self.table_name}: {str(e)}")
            raise DatabaseException(f"Failed to retrieve records: {str(e)}")
    
    def find_by_id(self, id: Any) -> Optional[T]:
        """Find a record by ID"""
        try:
            response = self.db.get_table(self.table_name).select("*").eq("id", id).execute()
            
            if response.data:
                return self.to_entity(response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error finding record by ID in {self.table_name}: {str(e)}")
            raise DatabaseException(f"Failed to find record: {str(e)}")
    
    def create(self, entity: T) -> T:
        """Create a new record"""
        try:
            data = self.to_dict(entity)
            response = self.db.get_table(self.table_name).insert(data).execute()
            
            if response.data:
                return self.to_entity(response.data[0])
            raise DatabaseException("Failed to create record")
        except Exception as e:
            logger.error(f"Error creating record in {self.table_name}: {str(e)}")
            raise DatabaseException(f"Failed to create record: {str(e)}")
    
    def create_many(self, entities: List[T]) -> List[T]:
        """Create multiple records"""
        try:
            data_list = [self.to_dict(entity) for entity in entities]
            response = self.db.get_table(self.table_name).insert(data_list).execute()
            
            if response.data:
                return [self.to_entity(row) for row in response.data]
            return []
        except Exception as e:
            logger.error(f"Error creating multiple records in {self.table_name}: {str(e)}")
            raise DatabaseException(f"Failed to create records: {str(e)}")
    
    def update(self, id: Any, entity: T) -> Optional[T]:
        """Update a record by ID"""
        try:
            data = self.to_dict(entity)
            # Remove id from data if present to avoid conflicts
            data.pop('id', None)
            
            response = self.db.get_table(self.table_name).update(data).eq("id", id).execute()
            
            if response.data:
                return self.to_entity(response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error updating record in {self.table_name}: {str(e)}")
            raise DatabaseException(f"Failed to update record: {str(e)}")
    
    def delete(self, id: Any) -> bool:
        """Delete a record by ID"""
        try:
            response = self.db.get_table(self.table_name).delete().eq("id", id).execute()
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Error deleting record from {self.table_name}: {str(e)}")
            raise DatabaseException(f"Failed to delete record: {str(e)}")
    
    def exists(self, id: Any) -> bool:
        """Check if a record exists by ID"""
        try:
            response = self.db.get_table(self.table_name).select("id").eq("id", id).execute()
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Error checking record existence in {self.table_name}: {str(e)}")
            raise DatabaseException(f"Failed to check record existence: {str(e)}")