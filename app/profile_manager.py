# app/profile_manager.py
from __future__ import annotations
import os
import json
from typing import List, Dict, Any


def default_characters_template() -> Dict[str, Any]:
    return {
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


class ProfileManager:
    """
    Profile = a folder under profiles_root containing characters.json
      profiles/<profile_name>/characters.json

    Example:
      profiles/default/characters.json
      profiles/gameA/characters.json
    """

    def __init__(self, profiles_root: str):
        self.profiles_root = os.path.abspath(profiles_root)
        os.makedirs(self.profiles_root, exist_ok=True)

    def _profile_dir(self, name: str) -> str:
        safe = name.strip().replace("\\", "_").replace("/", "_")
        return os.path.join(self.profiles_root, safe)

    def characters_path(self, profile_name: str) -> str:
        return os.path.join(self._profile_dir(profile_name), "characters.json")

    def ensure_profile(self, profile_name: str) -> str:
        """
        Ensure profile dir + characters.json exists.
        If missing, create it with default template.
        Returns characters.json path.
        """
        pdir = self._profile_dir(profile_name)
        os.makedirs(pdir, exist_ok=True)

        cpath = os.path.join(pdir, "characters.json")
        if not os.path.exists(cpath):
            with open(cpath, "w", encoding="utf-8") as f:
                json.dump(default_characters_template(), f, ensure_ascii=False, indent=2)
        return cpath

    def list_profiles(self) -> List[str]:
        """
        List existing profiles (folders containing characters.json).
        """
        profiles: List[str] = []
        for name in os.listdir(self.profiles_root):
            pdir = os.path.join(self.profiles_root, name)
            if not os.path.isdir(pdir):
                continue
            cpath = os.path.join(pdir, "characters.json")
            if os.path.exists(cpath):
                profiles.append(name)
        profiles.sort()
        return profiles

    def profile_exists(self, profile_name: str) -> bool:
        return os.path.exists(self.characters_path(profile_name))
