from typing import Dict, List, Optional
from datetime import datetime
from pymongo import MongoClient, ASCENDING
import json
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import logging
import random
import string

logger = logging.getLogger(__name__)


class ChatSession:
    """聊天会话类"""
    def __init__(self, _id=None, name: str = "", status: str = "active"):
        self._id = _id  # ObjectId 类型或None
        self.name = name or f"会话 {str(_id)[:8] if _id else ''}"
        self.messages: List[Dict] = []
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        self.status = status
        self.last_sync = datetime.now().isoformat()
        self.metadata: Dict = {}

    def add_message(self, role: str, content: str):
        """添加消息"""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        self.updated_at = datetime.now().isoformat()

    def clear_messages(self):
        """清空消息"""
        self.messages = []
        self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        d = {
            "name": self.name,
            "messages": self.messages,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status,
            "last_sync": self.last_sync,
            "metadata": self.metadata
        }
        if self._id:
            d["_id"] = self._id
        return d

    @classmethod
    def from_dict(cls, data: dict) -> 'ChatSession':
        session = cls(
            data.get("_id"),
            data["name"],
            data.get("status", "active")
        )
        session.messages = data.get("messages", [])
        session.created_at = data["created_at"]
        session.updated_at = data["updated_at"]
        session.last_sync = data.get("last_sync", session.created_at)
        session.metadata = data.get("metadata", {})
        return session

class SessionManager:
    """同步会话管理器"""
    def __init__(self, mongo_uri: str):
        self.client = MongoClient(mongo_uri)
        self.db = self.client.get_default_database()
        self.sessions = self.db.sessions
        self.messages = self.db.messages
        self._ensure_indexes()

    def _ensure_indexes(self):
        self.sessions.create_index("updated_at")
        self.messages.create_index([("session_id", 1), ("timestamp", ASCENDING)])

    def create_session(self, name: str = "") -> ChatSession:
        """创建新会话"""
        session = ChatSession(name=name)
        result = self.sessions.insert_one(session.to_dict())
        session._id = result.inserted_id  # ObjectId 类型
        return session

    def get_session(self, _id: str) -> Optional[ChatSession]:
        """获取会话"""
        session_dict = self.sessions.find_one({"_id": ObjectId(_id)})
        if session_dict:
            return ChatSession.from_dict(session_dict)
        return None

    def delete_session(self, _id: str) -> bool:
        """删除会话"""
        result = self.sessions.delete_one({"_id": ObjectId(_id)})
        self.messages.delete_many({"session_id": _id})
        return result.deleted_count > 0

    def list_sessions(self) -> List[Dict]:
        """列出所有会话，按更新时间降序"""
        sessions = []
        for session in self.sessions.find({"status": "active"}).sort("updated_at", -1):
            message_count = self.messages.count_documents({"session_id": str(session["_id"])})
            sessions.append({
                "_id": str(session["_id"]),
                "name": session["name"],
                "message_count": message_count,
                "updated_at": session["updated_at"],
                "last_sync": session.get("last_sync", session["created_at"])
            })
        return sessions

    def rename_session(self, _id: str, new_name: str) -> bool:
        """重命名会话"""
        result = self.sessions.update_one(
            {"_id": ObjectId(_id)},
            {"$set": {"name": new_name, "updated_at": datetime.now().isoformat()}}
        )
        return result.modified_count > 0

    def add_message(self, _id: str, role: str, content: str):
        """添加消息"""
        message = {
            "session_id": str(_id),
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        self.messages.insert_one(message)
        self.sessions.update_one(
            {"_id": ObjectId(_id)},
            {"$set": {"updated_at": message["timestamp"]}}
        )

    def get_messages(self, _id: str) -> List[Dict]:
        """获取会话的所有消息"""
        return list(self.messages.find(
            {"session_id": str(_id)},
            sort=[("timestamp", ASCENDING)]
        ))

    def clear_messages(self, _id: str):
        """清空会话消息"""
        self.messages.delete_many({"session_id": str(_id)})
        self.sessions.update_one(
            {"_id": ObjectId(_id)},
            {"$set": {"updated_at": datetime.now().isoformat()}}
        )

    def update_session_metadata(self, _id: str, metadata: Dict):
        """更新会话元数据"""
        self.sessions.update_one(
            {"_id": ObjectId(_id)},
            {"$set": {"metadata": metadata, "updated_at": datetime.now().isoformat()}}
        )

    def archive_session(self, _id: str):
        """归档会话"""
        self.sessions.update_one(
            {"_id": ObjectId(_id)},
            {"$set": {"status": "archived", "updated_at": datetime.now().isoformat()}}
        )

class AsyncSessionManager:
    """异步会话管理器"""
    def __init__(self, mongo_uri: str):
        self.client = AsyncIOMotorClient(mongo_uri, maxPoolSize=50)
        self.db = self.client.get_default_database()
        self.sessions = self.db.sessions
        self.messages = self.db.messages
        self._sync_task = None
        self._sync_interval = 5  # 同步间隔（秒）

    async def init_indexes(self):
        """初始化数据库索引"""
        await self.sessions.create_index("updated_at")
        await self.messages.create_index([("session_id", 1), ("timestamp", 1)])

    def start_sync(self):
        """启动自动同步任务"""
        if self._sync_task is None:
            self._sync_task = asyncio.create_task(self._auto_sync())

    def stop_sync(self):
        """停止自动同步任务"""
        if self._sync_task:
            self._sync_task.cancel()
            self._sync_task = None

    async def _auto_sync(self):
        """自动同步任务"""
        try:
            while True:
                await self._sync_all_sessions()
                await asyncio.sleep(self._sync_interval)
        except asyncio.CancelledError:
            logger.info("Auto sync task cancelled")
        except Exception as e:
            logger.error(f"Auto sync error: {e}")

    async def _sync_all_sessions(self):
        """同步所有活动会话"""
        cursor = self.sessions.find({"status": "active"})
        async for session in cursor:
            try:
                await self._sync_session(str(session["_id"]))
            except Exception as e:
                logger.error(f"Error syncing session {session['_id']}: {e}")

    async def _sync_session(self, _id: str):
        """同步单个会话"""
        session = await self.get_session(_id)
        if session:
            await self.sessions.update_one(
                {"_id": ObjectId(_id)},
                {
                    "$set": {
                        "last_sync": datetime.now().isoformat(),
                        "metadata": session.metadata
                    }
                }
            )

    async def create_session(self):
        # 生成随机后缀
        rand_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        session_name = f"会话-{rand_suffix}"
        session = ChatSession(name=session_name)
        result = await self.sessions.insert_one(session.to_dict())
        session._id = result.inserted_id
        return session

    async def get_session(self, _id: str) -> Optional[ChatSession]:
        """获取会话"""
        session_dict = await self.sessions.find_one({"_id": ObjectId(_id)})
        if session_dict:
            return ChatSession.from_dict(session_dict)
        return None

    async def delete_session(self, _id: str) -> bool:
        """删除会话"""
        result = await self.sessions.delete_one({"_id": ObjectId(_id)})
        await self.messages.delete_many({"session_id": str(_id)})
        return result.deleted_count > 0

    async def list_sessions(self) -> List[Dict]:
        """列出所有会话，按更新时间降序"""
        cursor = self.sessions.find({"status": "active"}).sort("updated_at", -1)
        sessions = []
        async for session in cursor:
            message_count = await self.messages.count_documents({"session_id": str(session["_id"])})
            sessions.append({
                "_id": str(session["_id"]),
                "name": session["name"],
                "message_count": message_count,
                "updated_at": session["updated_at"],
                "last_sync": session.get("last_sync", session["created_at"])
            })
        return sessions

    async def rename_session(self, session_id: str, new_name: str) -> bool:
        """重命名会话"""
        result = await self.sessions.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {"name": new_name, "updated_at": datetime.now().isoformat()}}
        )
        return result.modified_count > 0

    async def add_message_obj(self, message: dict):
        """添加消息体到会话"""
        message['timestamp'] = datetime.now().isoformat()
        insert_result = await self.messages.insert_one(message)
        await self.sessions.update_one(
            {"_id": ObjectId(message['session_id'])},
            {"$set": {"updated_at": datetime.now().isoformat()}}
        )
        logger.info(f" save message: session_id: {message}")
        return insert_result

    async def add_message(self, session_id: str, role: str, content: str, **kwargs):
        """添加消息到会话"""
        message = {
            "session_id": str(session_id),
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            **kwargs
        }
        insert_result = await self.messages.insert_one(message)
        await self.sessions.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {"updated_at": datetime.now().isoformat()}}
        )
        logger.info(f" save message: session_id: {session_id}, role: {role}, content: {content}")
        return insert_result

    async def get_messages(self, session_id: str) -> List[Dict]:
        """获取会话的所有消息"""
        cursor = self.messages.find(
            {"session_id": str(session_id)},
            sort=[("timestamp", 1)]
        )
        return [message async for message in cursor]

    async def clear_messages(self, session_id: str) -> bool:
        """清空会话消息"""
        await self.messages.delete_many({"session_id": str(session_id)})
        await self.sessions.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {"updated_at": datetime.now().isoformat()}}
        )
        return True

    async def update_message_content(self, message_id: str, content: str):
        """更新会话元数据"""
        await self.messages.update_one(
            {"_id": ObjectId(message_id)},
            {
                "$set": {
                    "content": content,
                    "updated_at": datetime.now().isoformat()
                }
            }
        )

    async def update_session_metadata(self, session_id: str, metadata: Dict):
        """更新会话元数据"""
        await self.sessions.update_one(
            {"_id": ObjectId(session_id)},
            {
                "$set": {
                    "metadata": metadata,
                    "updated_at": datetime.now().isoformat()
                }
            }
        )

    async def archive_session(self, session_id: str):
        """归档会话"""
        await self.sessions.update_one(
            {"_id": ObjectId(session_id)},
            {
                "$set": {
                    "status": "archived",
                    "updated_at": datetime.now().isoformat()
                }
            }
        ) 