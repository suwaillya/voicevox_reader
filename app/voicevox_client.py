# app/voicevox_client.py
from __future__ import annotations
import requests
from typing import Any, Dict, List, Optional


class VoiceVoxClient:
    """
    Minimal VOICEVOX Engine client.

    Typical flow:
      client = VoiceVoxClient()
      wav_bytes = client.synthesize("こんにちは", style_id=2)
    """

    def __init__(self, base_url: str = "http://127.0.0.1:50021", timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _url(self, path: str) -> str:
        if not path.startswith("/"):
            path = "/" + path
        return self.base_url + path

    def get_speakers(self) -> List[Dict[str, Any]]:
        """
        GET /speakers
        Returns:
            list of speakers with styles.
        """
        res = requests.get(self._url("/speakers"), timeout=self.timeout)
        res.raise_for_status()
        return res.json()

    def audio_query(self, text: str, style_id: int) -> Dict[str, Any]:
        """
        POST /audio_query?text=...&speaker=style_id
        Returns:
            audio query JSON.
        """
        res = requests.post(
            self._url("/audio_query"),
            params={"text": text, "speaker": style_id},
            timeout=self.timeout,
        )
        res.raise_for_status()
        return res.json()

    def synthesis(self, query: Dict[str, Any], style_id: int) -> bytes:
        """
        POST /synthesis?speaker=style_id
        Body: audio_query JSON
        Returns:
            wav bytes
        """
        res = requests.post(
            self._url("/synthesis"),
            params={"speaker": style_id},
            json=query,
            timeout=self.timeout,
        )
        res.raise_for_status()
        return res.content

    def synthesize(
        self,
        text: str,
        style_id: int,
        voice_params: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        """
        High-level helper: audio_query + (optional param override) + synthesis.

        voice_params can override audio_query fields:
            speedScale, pitchScale, intonationScale, volumeScale, etc.
        """
        query = self.audio_query(text, style_id)

        if voice_params:
            for k, v in voice_params.items():
                if k in query:
                    query[k] = v

        return self.synthesis(query, style_id)
