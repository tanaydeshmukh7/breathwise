"""MongoDB Atlas Async database layer using PyMongo AsyncMongoClient.

Includes collection schema validators, indexes, and a development-only
in-memory fallback when MONGODB_URI is not configured in development mode.
"""

from __future__ import annotations

import logging
import re
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from fastapi import HTTPException, status
from pymongo import ASCENDING, DESCENDING, AsyncMongoClient
from pymongo.errors import PyMongoError

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

COLLECTIONS = (
    "users",
    "family_profiles",
    "aqi_history",
    "recommendations",
    "routines",
    "conversations",
    "sustainable_actions",
    "user_preferences",
)

COLLECTION_VALIDATORS: dict[str, dict[str, Any]] = {
    "users": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["email", "name", "password_hash", "created_at"],
            "properties": {
                "email": {"bsonType": "string"},
                "name": {"bsonType": "string"},
                "password_hash": {"bsonType": "string"},
            },
        }
    },
    "family_profiles": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["user_id", "name", "member_type", "created_at"],
            "properties": {
                "member_type": {"enum": ["adult", "child", "elderly"]},
            },
        }
    },
    "aqi_history": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["location_key", "recorded_at", "data_source"],
        }
    },
    "recommendations": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["kind", "created_at"],
        }
    },
    "routines": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["user_id", "title", "items", "created_at"],
        }
    },
    "conversations": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["user_id", "messages", "updated_at"],
        }
    },
    "sustainable_actions": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["user_id", "category", "action_name", "completed_at"],
        }
    },
    "user_preferences": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["user_id", "updated_at"],
        }
    },
}


class InsertOneResult:
    def __init__(self, inserted_id: ObjectId) -> None:
        self.inserted_id = inserted_id


class UpdateResult:
    def __init__(self, matched_count: int, modified_count: int, upserted_id: ObjectId | None = None) -> None:
        self.matched_count = matched_count
        self.modified_count = modified_count
        self.upserted_id = upserted_id


class DeleteResult:
    def __init__(self, deleted_count: int) -> None:
        self.deleted_count = deleted_count


def _match_filter(doc: dict[str, Any], flt: dict[str, Any]) -> bool:
    for key, expected in flt.items():
        if key == "$or":
            if not any(_match_filter(doc, sub) for sub in expected):
                return False
            continue
        actual = doc.get(key)
        if isinstance(expected, dict):
            for op, val in expected.items():
                if op == "$gte" and (actual is None or actual < val):
                    return False
                if op == "$lte" and (actual is None or actual > val):
                    return False
                if op == "$gt" and (actual is None or actual <= val):
                    return False
                if op == "$lt" and (actual is None or actual >= val):
                    return False
                if op == "$in" and actual not in val:
                    return False
                if op == "$ne" and actual == val:
                    return False
                if op == "$regex":
                    if actual is None or not re.search(val, str(actual), re.IGNORECASE):
                        return False
        else:
            if actual != expected:
                return False
    return True


class InMemoryCursor:
    """Async cursor shim for development in-memory fallback."""

    def __init__(self, docs: list[dict[str, Any]]) -> None:
        self._docs = docs
        self._skip = 0
        self._limit: int | None = None

    def sort(self, key_or_list: str | list[tuple[str, int]], direction: int = ASCENDING) -> "InMemoryCursor":
        if isinstance(key_or_list, str):
            specs = [(key_or_list, direction)]
        else:
            specs = key_or_list
        for field, order in reversed(specs):
            self._docs.sort(
                key=lambda d: (d.get(field) is None, d.get(field) or ""),
                reverse=(order == DESCENDING),
            )
        return self

    def skip(self, count: int) -> "InMemoryCursor":
        self._skip = max(0, count)
        return self

    def limit(self, count: int) -> "InMemoryCursor":
        self._limit = max(0, count)
        return self

    async def to_list(self, length: int | None = None) -> list[dict[str, Any]]:
        sliced = self._docs[self._skip :]
        cap = self._limit if self._limit is not None else length
        if cap is not None:
            sliced = sliced[:cap]
        return [deepcopy(d) for d in sliced]


class InMemoryCollection:
    """Development-only async collection shim matching PyMongo AsyncCollection methods."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._docs: list[dict[str, Any]] = []

    async def find_one(self, flt: dict[str, Any]) -> dict[str, Any] | None:
        for doc in self._docs:
            if _match_filter(doc, flt):
                return deepcopy(doc)
        return None

    def find(self, flt: dict[str, Any] | None = None) -> InMemoryCursor:
        flt = flt or {}
        matched = [deepcopy(d) for d in self._docs if _match_filter(d, flt)]
        return InMemoryCursor(matched)

    async def insert_one(self, doc: dict[str, Any]) -> InsertOneResult:
        copy = deepcopy(doc)
        if "_id" not in copy:
            copy["_id"] = ObjectId()
        self._docs.append(copy)
        return InsertOneResult(copy["_id"])

    async def update_one(
        self, flt: dict[str, Any], update: dict[str, Any], upsert: bool = False
    ) -> UpdateResult:
        for idx, doc in enumerate(self._docs):
            if _match_filter(doc, flt):
                if "$set" in update:
                    doc.update(deepcopy(update["$set"]))
                if "$push" in update:
                    for k, v in update["$push"].items():
                        arr = doc.setdefault(k, [])
                        if isinstance(v, dict) and "$each" in v:
                            arr.extend(deepcopy(v["$each"]))
                        else:
                            arr.append(deepcopy(v))
                self._docs[idx] = doc
                return UpdateResult(1, 1)
        if upsert:
            new_doc: dict[str, Any] = {"_id": ObjectId()}
            for k, v in flt.items():
                if not k.startswith("$"):
                    new_doc[k] = deepcopy(v)
            if "$set" in update:
                new_doc.update(deepcopy(update["$set"]))
            self._docs.append(new_doc)
            return UpdateResult(0, 0, upserted_id=new_doc["_id"])
        return UpdateResult(0, 0)

    async def delete_one(self, flt: dict[str, Any]) -> DeleteResult:
        for idx, doc in enumerate(self._docs):
            if _match_filter(doc, flt):
                del self._docs[idx]
                return DeleteResult(1)
        return DeleteResult(0)

    async def delete_many(self, flt: dict[str, Any]) -> DeleteResult:
        before = len(self._docs)
        self._docs = [d for d in self._docs if not _match_filter(d, flt)]
        return DeleteResult(before - len(self._docs))

    async def count_documents(self, flt: dict[str, Any] | None = None) -> int:
        flt = flt or {}
        return sum(1 for d in self._docs if _match_filter(d, flt))

    async def create_index(self, *args: Any, **kwargs: Any) -> str:
        return "in_memory_index"


class DatabaseHandle:
    """Unified handle exposing the 8 BreatheWise MongoDB collections."""

    def __init__(self, db_obj: Any, mode: str, detail: str) -> None:
        self._db = db_obj
        self.mode = mode  # "mongodb_atlas" | "dev_memory_fallback" | "unavailable"
        self.detail = detail

    @property
    def is_connected(self) -> bool:
        return self.mode in ("mongodb_atlas", "dev_memory_fallback")

    def __getattr__(self, name: str) -> Any:
        if name in COLLECTIONS:
            return self._db[name]
        raise AttributeError(name)


class InMemoryDatabase:
    def __init__(self) -> None:
        self._collections = {name: InMemoryCollection(name) for name in COLLECTIONS}

    def __getitem__(self, name: str) -> InMemoryCollection:
        return self._collections[name]


class DatabaseManager:
    """Manages PyMongo AsyncMongoClient lifecycle, validators, and indexes."""

    def __init__(self) -> None:
        self.client: AsyncMongoClient | None = None
        self.handle: DatabaseHandle | None = None

    async def connect(self, settings: Settings) -> DatabaseHandle:
        uri = settings.MONGODB_URI.strip()
        if uri:
            try:
                client: AsyncMongoClient = AsyncMongoClient(
                    uri,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=5000,
                )
                await client.aconnect()
                await client.admin.command("ping")
                db = client[settings.MONGODB_DB_NAME]
                await self._ensure_collections_and_indexes(db)
                self.client = client
                self.handle = DatabaseHandle(
                    db,
                    mode="mongodb_atlas",
                    detail="Connected to MongoDB via PyMongo AsyncMongoClient.",
                )
                logger.info("Connected to MongoDB database '%s'.", settings.MONGODB_DB_NAME)
                return self.handle
            except Exception as exc:
                logger.warning("MongoDB connection failed: %s", exc)
                if settings.ENVIRONMENT == "development" and settings.DEV_MEMORY_DB_FALLBACK:
                    self.handle = DatabaseHandle(
                        InMemoryDatabase(),
                        mode="dev_memory_fallback",
                        detail=f"MongoDB unreachable ({type(exc).__name__}); using development in-memory store.",
                    )
                    return self.handle
                self.handle = DatabaseHandle(
                    None,
                    mode="unavailable",
                    detail="MongoDB connection failed. Verify MONGODB_URI.",
                )
                return self.handle

        # MONGODB_URI not configured
        if settings.ENVIRONMENT == "development" and settings.DEV_MEMORY_DB_FALLBACK:
            logger.info("MONGODB_URI not set; running with development in-memory fallback.")
            self.handle = DatabaseHandle(
                InMemoryDatabase(),
                mode="dev_memory_fallback",
                detail="MONGODB_URI not configured; using development in-memory store (non-persistent).",
            )
            return self.handle

        self.handle = DatabaseHandle(
            None,
            mode="unavailable",
            detail="MONGODB_URI is not configured.",
        )
        return self.handle

    async def _ensure_collections_and_indexes(self, db: Any) -> None:
        existing = set(await db.list_collection_names())
        for col_name in COLLECTIONS:
            validator = COLLECTION_VALIDATORS.get(col_name)
            if col_name not in existing:
                try:
                    await db.create_collection(
                        col_name,
                        validator=validator,
                        validationLevel="moderate",
                    )
                except PyMongoError as exc:
                    logger.debug("create_collection(%s) skipped: %s", col_name, exc)
            elif validator:
                try:
                    await db.command(
                        {
                            "collMod": col_name,
                            "validator": validator,
                            "validationLevel": "moderate",
                        }
                    )
                except PyMongoError as exc:
                    logger.debug("collMod(%s) skipped: %s", col_name, exc)

        # Indexes
        await db["users"].create_index([("email", ASCENDING)], unique=True)
        await db["family_profiles"].create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
        await db["aqi_history"].create_index(
            [("location_key", ASCENDING), ("recorded_at", DESCENDING)]
        )
        await db["aqi_history"].create_index(
            [("created_at", ASCENDING)], expireAfterSeconds=60 * 60 * 24 * 30
        )
        await db["recommendations"].create_index(
            [("user_id", ASCENDING), ("created_at", DESCENDING)]
        )
        await db["routines"].create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
        await db["conversations"].create_index(
            [("user_id", ASCENDING), ("updated_at", DESCENDING)]
        )
        await db["conversations"].create_index(
            [("updated_at", ASCENDING)], expireAfterSeconds=60 * 60 * 24 * 90
        )
        await db["sustainable_actions"].create_index(
            [("user_id", ASCENDING), ("completed_at", DESCENDING)]
        )
        await db["user_preferences"].create_index([("user_id", ASCENDING)], unique=True)

    async def close(self) -> None:
        if self.client is not None:
            await self.client.close()
            self.client = None


db_manager = DatabaseManager()


async def get_db() -> DatabaseHandle:
    if db_manager.handle is None:
        settings = get_settings()
        await db_manager.connect(settings)
    if db_manager.handle is None or not db_manager.handle.is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "database_unavailable",
                "message": db_manager.handle.detail if db_manager.handle else "Database not initialized.",
                "configuration_required": "Set MONGODB_URI in backend/.env to connect MongoDB Atlas.",
            },
        )
    return db_manager.handle


async def get_optional_db() -> DatabaseHandle | None:
    """Return DatabaseHandle when connected, or None so public telemetry/AI routes stay available."""
    if db_manager.handle is None:
        settings = get_settings()
        await db_manager.connect(settings)
    if db_manager.handle is not None and db_manager.handle.is_connected:
        return db_manager.handle
    return None


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
