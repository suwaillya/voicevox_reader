# app/queue_manager.py
from __future__ import annotations
import threading
import queue
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any

from voicevox_client import VoiceVoxClient
from player import AudioPlayer
from text_cleaner import preprocess
from config import CharacterConfig


@dataclass
class SpeakItem:
    name: str
    text: str
    style_id: int
    voice_params: Optional[Dict[str, Any]] = None
    no_dedup: bool = False

    def dedup_key(self) -> tuple:
        vp = tuple(sorted((self.voice_params or {}).items()))
        return (self.text, self.style_id, vp)


class SpeechQueueManager:
    def __init__(
        self,
        voicevox_url: str = "http://127.0.0.1:50021",
        characters_path: str = "../config/characters.json",
        dedup_enabled: bool = True,
        max_queue_size: int = 100,
    ):
        self.client = VoiceVoxClient(voicevox_url)

        # ✅ blocksize smaller -> faster interrupt response
        self.player = AudioPlayer(blocksize=256)

        self.characters = CharacterConfig(characters_path)
        self._characters_path = characters_path

        self.dedup_enabled = dedup_enabled
        self.q: queue.Queue[SpeakItem] = queue.Queue(maxsize=max_queue_size)

        self._stop_flag = threading.Event()
        self._started = False
        self._last_spoken_key = None

        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)

    def start(self):
        if self._started:
            return
        self._started = True
        print("[QueueManager] Worker started")
        self._worker_thread.start()

    def load_characters_path(self, characters_path: str):
        print("[QueueManager] Loading characters from:", characters_path)
        self.characters = CharacterConfig(characters_path)
        self._characters_path = characters_path

    def get_current_characters_path(self) -> str:
        return getattr(self, "_characters_path", "")

    def enqueue(
        self,
        text: str,
        name: str = "default",
        style_id: Optional[int] = None,
        voice_params: Optional[Dict[str, Any]] = None,
        no_dedup: bool = False
    ) -> bool:
        if not text or not text.strip():
            return False

        clean = preprocess(text)
        if not clean:
            return False

        # Resolve base from profile
        resolved_style_id, resolved_params = self.characters.resolve(name)

        # ✅ Apply overrides (FIXED)
        final_style_id = style_id if style_id is not None else resolved_style_id
        final_params = dict(resolved_params)
        if voice_params:
            final_params.update(voice_params)

        item = SpeakItem(
            name=name,
            text=clean,
            style_id=final_style_id,
            voice_params=final_params,
            no_dedup=no_dedup
        )

        try:
            self.q.put_nowait(item)
            return True
        except queue.Full:
            return False

    def stop_current(self):
        """
        Immediately stop playback + signal worker loop.
        """
        self.player.stop()
        self._stop_flag.set()
        # yield a tiny bit so worker sees it immediately
        time.sleep(0.001)
        self._stop_flag.clear()

    def clear_queue(self):
        try:
            while True:
                self.q.get_nowait()
        except queue.Empty:
            pass

    def enqueue_interrupt(self, text, name="default", style_id=None, voice_params=None, no_dedup=False):
        """
        Interrupt mode: stop current playback, clear queue, then enqueue new item.
        """
        self.stop_current()
        self.clear_queue()
        return self.enqueue(text, name=name, style_id=style_id, voice_params=voice_params, no_dedup=no_dedup)

    def _worker_loop(self):
        print("[QueueManager] Worker loop running")
        while True:
            item = self.q.get()
            print(f"[QueueManager] Dequeued: name={item.name}, style_id={item.style_id}, text={item.text}")

            key = item.dedup_key()
            if (not item.no_dedup) and self.dedup_enabled and key == self._last_spoken_key:
                print("[QueueManager] Dedup skipped (same text+voice)")
                continue

            try:
                wav_bytes = self.client.synthesize(
                    item.text,
                    style_id=item.style_id,
                    voice_params=item.voice_params
                )

                # ✅ This hard-interrupts previous audio immediately by token change
                self.player.play(wav_bytes)

                # Wait until finished; interrupt will stop it immediately
                while self.player.is_playing():
                    if self._stop_flag.is_set():
                        # stop_current already calls player.stop()
                        break
                    time.sleep(0.01)

                if not self._stop_flag.is_set():
                    self._last_spoken_key = key

            except Exception as e:
                print("[QueueManager] TTS error:", repr(e))
