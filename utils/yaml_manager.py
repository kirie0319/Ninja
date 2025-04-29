# utils/yaml_manager.py
import yaml, os, re, shutil, aiofiles, asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional 
from datetime import datetime

class YAMLManager:
    """the class for managing the yaml prompt file"""
    def __init__(self, base_dir: str):
        """ Initialize"""
        self.base_dir = Path(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    def _sanitize_filename(self, filename: str) -> str:
        return re.sub(r'[^\w\-\.]', '_', filename)

    def save_prompt(self, category: str, name: str, content: Dict[str, Any], author: str = "system") -> str:
        category_dir = self.base_dir / self._sanitize_filename(category)
        os.makedirs(category_dir, exist_ok=True)
        file_name = f"{self._sanitize_filename(name)}.yaml"
        file_path = category_dir / file_name

        if not content.get('metadata'):
            content['metadata'] = {}

        content['metadata']['author'] = author 

        if file_path.exists():
            existing_content = self.load_prompt(category, name)

            if not content.get('versions'):
                content['versions'] = {}

            current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            version_key = f"v_{current_time}"

            if existing_content:
                content['versions'][version_key] = {
                    'content': existing_content.get('prompt', ''),
                    'metadata': existing_content.get('metadata', {}),
                    'timestamp': curren_time
                }
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(content, f, allow_unicode=True, sort_keys=False)
        return str(file_path)

    async def load_prompt(self, category: str, name: str) -> Optional[Dict[str, Any]]:
        file_path = self.base_dir / self._sanitize_filename(category) / f"{self._sanitize_filename(name)}.yaml"

        if not file_path.exists():
            return None 
        
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                try:
                    return yaml.safe_load(content)
                except yaml.YAMLError:
                    return None 
        except FileNotFoundError:
            return None
