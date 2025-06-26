import motor.motor_asyncio
from typing import List, Dict, Any, Type, TypeVar, Optional, Generic
from bson import ObjectId
from pydantic import BaseModel

# Connect to MongoDB
client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017")
db = client.rocket_league_db

# Generic type for models
ModelType = TypeVar("ModelType", bound=BaseModel)

class BaseRepository(Generic[ModelType]):
    """Base repository for MongoDB operations"""
    
    def __init__(self, model: Type[ModelType], collection_name: str):
        self.model = model
        self.collection = db[collection_name]
    
    async def get(self, id: str) -> Optional[ModelType]:
        """Get a document by id"""
        doc = await self.collection.find_one({"_id": ObjectId(id)})
        if doc:
            return self.model(**doc)
        return None
    
    async def get_all(self) -> List[ModelType]:
        """Get all documents in the collection"""
        cursor = self.collection.find()
        results = []
        async for doc in cursor:
            results.append(self.model(**doc))
        return results
    
    async def create(self, obj: ModelType) -> ModelType:
        """Create a new document"""
        doc = obj.dict(by_alias=True)
        if "_id" not in doc or not doc["_id"]:
            doc.pop("_id", None)
        result = await self.collection.insert_one(doc)
        return await self.get(str(result.inserted_id))
    
    async def update(self, id: str, obj: Dict[str, Any]) -> Optional[ModelType]:
        """Update a document"""
        # Don't try to update _id
        update_data = {k: v for k, v in obj.items() if k != "_id"}
        await self.collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": update_data}
        )
        return await self.get(id)
    
    async def delete(self, id: str) -> bool:
        """Delete a document"""
        result = await self.collection.delete_one({"_id": ObjectId(id)})
        return result.deleted_count > 0
    
    async def find(self, query: Dict[str, Any]) -> List[ModelType]:
        """Find documents matching a query"""
        cursor = self.collection.find(query)
        results = []
        async for doc in cursor:
            results.append(self.model(**doc))
        return results