# utils/chatroom_manager.py
import uuid 
import os, json
from typing import Dict, List, Any, Optional, Tuple 
from datetime import datetime

from .file_operations import load_json, save_json, to_pretty_json

class ChatroomManager:
    def __init__(self, data_dir: str = "data", max_rallies: int = 6):
        self.data_dir = data_dir
        self.max_rallies = max_rallies
        self.chatroom_file = os.path.join(data_dir, "cahtroom.json")

        os.makedirs(data_dir, exist_ok=True)

        if not os.path.exists(self.chatroom_file):
            with open(self.chatroom_file, "w", encoding="utf-8") as f:
                f.write(json.dumps({}))

    async def get_user_files(self, user_id: str) -> Dict[str, str]:
        return {
            "chat_log": os.path.join(self.data_dir, f"chat_log_{user_id}.json"),
            "summary": os.path.join(self.data_dir, f"summary_{user_id}.json"),
            "user_history": os.path.join(self.data_dir, f"user_history_{user_id}.json")
        }

    async def get_or_create_chatroom(self, user_id: str) -> Dict[str, Any]:
        chatrooms = await load_json(self.chatroom_file, {})

        if user_id not in chatrooms:
            user_files = await self.get_user_files(user_id)

            await save_json(user_files["chat_log"], [])
            await save_json(user_files["summary"], [])
            await save_json(user_files["user_history"], {})

            chatrooms[user_id] = {
                "created_at": datetime.now().isoformat(),
                "files": user_files
            }
            await save_json(self.chatroom_file, chatrooms)
        return chatrooms[user_id]

    async def get_last_conversation_pair(self, user_id: str) -> Optional[Dict[str, Dict]]:
        chatroom = await self.get_or_create_chatroom(user_id)
        history = await load_json(chatroom["files"]["chat_log"], [])

        if len(history) < 2:
            return None 
        for i in range(len(history) - 2, -1, -1):
            if history[i]["role"] == "user" and history[i + 1]["role"] == "assistant":
                return {
                    "user": history[i],
                    "assistant": history[i + 1]
                }
        return None

    async def update_user_messages(self, user_id: str, message_pair: Dict[str, Any]) -> None:
        chatroom = await self.get_or_create_chatroom(user_id)
        user_history = await load_json(chatroom["files"]["user_history"], {})
        history = await load_json(chatroom["files"]["chat_log"], [])

        if user_id not in user_history:
            user_history[user_id] = {
                "created_at": datetime.now().isoformat(),
                "messages": []
            }
        if "messages" not in user_history[user_id]:
            user_history[user_id]["messages"] = []

        user_history[user_id]["messages"].append(message_pair)

        if len(history) > 2:
            user_history[user_id]["messages"] = []
        if len(user_history[user_id]["messages"]) > self.max_rallies:
            user_history[user_id]["messages"] = user_history[user_id]["messages"][-self.max_rallies:]

        await save_json(chatroom["files"]["user_history"], user_history)

    async def add_messages(self, user_id: str, message: Dict[str, Any]) -> None:
        chatroom = await self.get_or_create_chatroom(user_id)
        history = await load_json(chatroom["files"]["chat_log"], [])
        history.append(message)
        await save_json(chatroom["files"]["chat_log"], history)

    async def clear_chat_data(self, user_id: str) -> None:
        try:
            chatroom = await self.get_or_create_chatroom(user_id)
            user_files = chatroom["files"]

            await load_json(user_files["chat_log"], [])
            await load_json(user_files["summary"], [])
            await load_json(user_files["user_history"], {})

            return True
        except Exception as e:
            print(f"チャットデータクリア: {str(e)}")
            return False

    async def get_chat_data(self, user_id: str) -> Tuple[List, List, Dict]:
            """ユーザーのチャットデータを取得"""
            chatroom = await self.get_or_create_chatroom(user_id)
            user_files = chatroom["files"]
            
            history = await load_json(user_files["chat_log"], [])
            summary = await load_json(user_files["summary"], [])
            user_history = await load_json(user_files["user_history"], {})
            
            return history, summary, user_history