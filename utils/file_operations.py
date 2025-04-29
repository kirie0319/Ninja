# uitls/file_operations.py
from functools import lru_cache
import asyncio, aiofiles, json, os 
from typing import Any, Dict, List, Optional, Union 

CACHE_SIZE = 100

_json_cache = {}
_json_cache_ttl = {}
CACHE_TTL = 60

async def load_json(filepath: str, default: Any) -> Any:
    curren_time = asyncio.get_event_loop().time() 

    if filepath in _json_cache and filepath in _json_cache_ttl:
        if curren_time - _json_cache_ttl[filepath] < CACHE_TTL:
            return _json_cache[filepath]
    try:
        if not os.path.exists(filepath):
            _json_cache[filepath] = default
            _json_cache_ttl[filepath] = curren_time
            return default
        async with aiofiles.open(filepath, "r", encoding='utf-8') as f:
            content = await f.read()
            try:
                data = json.loads(content)
                _json_cache[filepath] = data 
                _json_cache_ttl[filepath] = curren_time
                return data 
            except json.JSONDecodeError:
                _json_cache[filepath] = default
                _json_cache_ttl[filepath] = curren_time
                return default
    except FileNotFoundError:
        _json_cache[filepath] = default
        _json_cache_ttl[filepath] = current_time
        return default

async def save_json(filepath: str, data: Any) -> None:
    try:
        if not filepath:
            print("Error: Empty filepath provided")
            return
        # print(filepath)
        # os.makedirs(os.path.dirname(filepath), exist_ok=True)

        async with aiofiles.open(filepath, "w", encoding='utf-8') as f:
            json_str = json.dumps(data, indent=2, ensure_ascii=False)
            await f.write(json_str)
        _json_cache[filepath] = data 
        _json_cache_ttl[filepath] = asyncio.get_event_loop().time()
    except Exception as e:
        print(f"保持エラー ({filepath}): {str(e)}")

async def to_pretty_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)

def clear_cache(filepath: Optional[str] = None) -> None:
    if filepath:
        if filepath in _json_cache:
            del _json_cache[filepath]
        if filepath in _json_cache_ttl:
            del _json_cache_ttl[filepath]
    else:
        _json_cache.clear()
        _json_cache_ttl.clear()


async def get_last_conversation(history_json: list) -> Optional[Dict[str, Dict]]:
    history = history_json

    if len(history) < 2:
        return None
    for i in range(len(history) - 2, -1, -1):
        if history[i]["role"] == "user" and history[i + 1]["role"] == "assistant":
            return {
                "user": history[i],
                "assistant": history[i + 1]
            }
    return None

async def clear_chat_data():
        
    await save_json("chat_log.json", [])
    await save_json("chatsummary.json", [])
    await save_json("user_history.json", {})