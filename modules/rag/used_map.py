import os
import json
from typing import Optional, Dict, List
from modules.utils.logger import CustomLogger

class UsedMap:
    def __init__(self, filepath: str = "data/used_chunks_map.json", logger=None):
        self.filepath = filepath
        self.logger = logger or CustomLogger("UsedMap")
        self.used_map: Dict[str, List[str]] = {}
        self.load()

    def mark_used(self, chunk_id: str, context: Optional[str] = None):
        context = context or "global"
        if chunk_id not in self.used_map:
            self.used_map[chunk_id] = []
        if context not in self.used_map[chunk_id]:
            self.used_map[chunk_id].append(context)
            self.logger.debug(f"Marked chunk '{chunk_id}' as used in context '{context}'")

    def was_used(self, chunk_id: str, context: Optional[str] = None) -> bool:
        context = context or "global"
        return context in self.used_map.get(chunk_id, [])

    def reset(self):
        self.used_map.clear()
        self.logger.info("Usage map reset.")

    def save(self):
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(self.used_map, f, indent=2)
        self.logger.info(f"Saved used map to {self.filepath}")

    def load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    self.used_map = json.load(f)
                self.logger.info(f"Loaded used map from {self.filepath}")
            except Exception as e:
                self.logger.warning(f"Failed to load used map: {e}")
                self.used_map = {}
        else:
            self.used_map = {}
            self.logger.info(f"No existing used map found at {self.filepath}, starting fresh")
