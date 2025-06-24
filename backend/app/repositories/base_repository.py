"""
Base Repository Pattern Implementation

Provides abstract base repository with common database operations
and transaction management using SQLAlchemy async sessions.
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List, Optional, Dict, Any, Type
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, update, delete, func
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import DatabaseManager
from app.utils.logger import get_logger

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")

logger = get_logger(__name__)


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType], ABC):
    """Abstract base repository providing common CRUD operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.session_factory = sessionmaker(
            bind=db_manager.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    @property
    @abstractmethod
    def model(self) -> Type[ModelType]:
        """Return the SQLAlchemy model class."""
        pass
    
    async def get_session(self) -> AsyncSession:
        """Get database session."""
        return self.session_factory()
    
    async def get_by_id(self, id: int) -> Optional[ModelType]:
        """Get entity by ID."""
        async with self.get_session() as session:
            try:
                result = await session.get(self.model, id)
                return result
            except SQLAlchemyError as e:
                logger.error(f"Error getting {self.model.__name__} by ID {id}: {e}")
                return None
    
    async def get_multi(
        self, 
        skip: int = 0, 
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelType]:
        """Get multiple entities with pagination and filtering."""
        async with self.get_session() as session:
            try:
                query = select(self.model)
                
                # Apply filters
                if filters:
                    for field, value in filters.items():
                        if hasattr(self.model, field):
                            column = getattr(self.model, field)
                            if isinstance(value, list):
                                query = query.where(column.in_(value))
                            else:
                                query = query.where(column == value)
                
                query = query.offset(skip).limit(limit)
                result = await session.execute(query)
                return result.scalars().all()
                
            except SQLAlchemyError as e:
                logger.error(f"Error getting multiple {self.model.__name__}: {e}")
                return []
    
    async def create(self, obj_in: CreateSchemaType) -> Optional[ModelType]:
        """Create new entity."""
        async with self.get_session() as session:
            try:
                # Convert Pydantic model to dict if needed
                if hasattr(obj_in, 'model_dump'):
                    create_data = obj_in.model_dump()
                elif hasattr(obj_in, 'dict'):
                    create_data = obj_in.dict()
                else:
                    create_data = obj_in
                
                db_obj = self.model(**create_data)
                session.add(db_obj)
                await session.commit()
                await session.refresh(db_obj)
                return db_obj
                
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Error creating {self.model.__name__}: {e}")
                return None
    
    async def update(
        self, 
        id: int, 
        obj_in: UpdateSchemaType
    ) -> Optional[ModelType]:
        """Update existing entity."""
        async with self.get_session() as session:
            try:
                # Get existing object
                db_obj = await session.get(self.model, id)
                if not db_obj:
                    return None
                
                # Convert Pydantic model to dict if needed
                if hasattr(obj_in, 'model_dump'):
                    update_data = obj_in.model_dump(exclude_unset=True)
                elif hasattr(obj_in, 'dict'):
                    update_data = obj_in.dict(exclude_unset=True)
                else:
                    update_data = obj_in
                
                # Update fields
                for field, value in update_data.items():
                    if hasattr(db_obj, field):
                        setattr(db_obj, field, value)
                
                await session.commit()
                await session.refresh(db_obj)
                return db_obj
                
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Error updating {self.model.__name__} with ID {id}: {e}")
                return None
    
    async def delete(self, id: int) -> bool:
        """Delete entity by ID."""
        async with self.get_session() as session:
            try:
                db_obj = await session.get(self.model, id)
                if not db_obj:
                    return False
                
                await session.delete(db_obj)
                await session.commit()
                return True
                
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Error deleting {self.model.__name__} with ID {id}: {e}")
                return False
    
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count entities with optional filters."""
        async with self.get_session() as session:
            try:
                query = select(func.count(self.model.id))
                
                # Apply filters
                if filters:
                    for field, value in filters.items():
                        if hasattr(self.model, field):
                            column = getattr(self.model, field)
                            if isinstance(value, list):
                                query = query.where(column.in_(value))
                            else:
                                query = query.where(column == value)
                
                result = await session.execute(query)
                return result.scalar() or 0
                
            except SQLAlchemyError as e:
                logger.error(f"Error counting {self.model.__name__}: {e}")
                return 0
    
    async def exists(self, id: int) -> bool:
        """Check if entity exists by ID."""
        async with self.get_session() as session:
            try:
                query = select(func.count(self.model.id)).where(self.model.id == id)
                result = await session.execute(query)
                return (result.scalar() or 0) > 0
                
            except SQLAlchemyError as e:
                logger.error(f"Error checking existence of {self.model.__name__} with ID {id}: {e}")
                return False
    
    async def bulk_create(self, objects: List[CreateSchemaType]) -> List[ModelType]:
        """Create multiple entities in bulk."""
        async with self.get_session() as session:
            try:
                db_objects = []
                for obj_in in objects:
                    # Convert Pydantic model to dict if needed
                    if hasattr(obj_in, 'model_dump'):
                        create_data = obj_in.model_dump()
                    elif hasattr(obj_in, 'dict'):
                        create_data = obj_in.dict()
                    else:
                        create_data = obj_in
                    
                    db_obj = self.model(**create_data)
                    db_objects.append(db_obj)
                
                session.add_all(db_objects)
                await session.commit()
                
                # Refresh all objects
                for db_obj in db_objects:
                    await session.refresh(db_obj)
                
                return db_objects
                
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Error bulk creating {self.model.__name__}: {e}")
                return []
    
    async def bulk_update(
        self, 
        updates: List[Dict[str, Any]]
    ) -> bool:
        """Update multiple entities in bulk."""
        async with self.get_session() as session:
            try:
                for update_data in updates:
                    id = update_data.pop('id')
                    query = update(self.model).where(self.model.id == id).values(**update_data)
                    await session.execute(query)
                
                await session.commit()
                return True
                
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Error bulk updating {self.model.__name__}: {e}")
                return False
    
    async def bulk_delete(self, ids: List[int]) -> bool:
        """Delete multiple entities in bulk."""
        async with self.get_session() as session:
            try:
                query = delete(self.model).where(self.model.id.in_(ids))
                await session.execute(query)
                await session.commit()
                return True
                
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Error bulk deleting {self.model.__name__}: {e}")
                return False