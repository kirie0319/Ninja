# utils/user_manager.py
import json, os, uuid, aiofiles 
from typing import Optional

USERS_FILE = "users.json"

async def load_users():
    async with aiofiles.open("users.json", "r", encoding="utf-8") as f:
        content = await f.read()
        return json.loads(content)

async def save_users(users: list):
    async with aiofiles.open("users.json", "w", encoding="utf-8") as f:
        await f.write(json.dumps(users, ensure_ascii=False, indent=2))

async def add_user(username: str, email: str, password: str) -> dict:
    users = await load_users()
    if any(u["email"] == email or u["username"] == username for u in users):
        raise ValueError("既に存在するユーザーです")

    new_user = {
        "id": str(uuid.uuid4()),
        'username': username,
        "email": email,
        "password": password
    }
    users.append(new_user)
    await save_users(users)
    return new_user

async def get_user_by_email_or_username(identifier: str) -> Optional[dict]:
    users = await load_users()
    for u in users:
        if u["email"] == identifier or u["username"] == identifier:
            return u 
    return None
