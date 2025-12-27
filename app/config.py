# app/config.py
from __future__ import annotations
import json
import os
from typing import Dict, Any, Optional


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge override into base (shallow for most keys, deep for nested dicts).
    """
    merged = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            merged[k] = deep_merge(merged[k], v)
        else:
            merged[k] = v
    return merged


class CharacterConfig:
    """
    Manage character -> VOICEVOX style_id + voice params.
    Stored in a json file (config/characters.json).
    """

    def __init__(self, path: str):
        self.path = path
        self.data: Dict[str, Any] = {}
        self.load()

    def load(self):
        if not os.path.exists(self.path):
            # Create minimal default if missing
            self.data = {
                "default": {
                    "style_id": 2,
                    "voice_params": {
                        "speedScale": 1.0,
                        "pitchScale": 0.0,
                        "intonationScale": 1.0,
                        "volumeScale": 1.0
                    }
                }
            }
            self.save()
            return

        with open(self.path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

        if "default" not in self.data:
            raise ValueError("characters.json must contain a 'default' entry")

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def get_profile(self, name: str) -> Dict[str, Any]:
        """
        Returns a merged profile: default + specific character override.
        """
        default = self.data.get("default", {})
        specific = self.data.get(name, {})
        return deep_merge(default, specific)

    def get_style_id(self, name: str) -> int:
        prof = self.get_profile(name)
        return int(prof.get("style_id", self.data["default"].get("style_id", 2)))

    def get_voice_params(self, name: str) -> Dict[str, Any]:
        prof = self.get_profile(name)
        return dict(prof.get("voice_params", {}))

    def resolve(self, name: str) -> tuple[int, Dict[str, Any]]:
        """
        Convenience function:
          returns (style_id, merged_voice_params)
        """
        return self.get_style_id(name), self.get_voice_params(name)
