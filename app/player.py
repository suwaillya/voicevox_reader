# app/player.py
from __future__ import annotations
import io
import threading
from typing import Optional

import numpy as np
import sounddevice as sd
import soundfile as sf


class AudioPlayer:
    """
    Hard-interruptible audio player using ONE persistent OutputStream.
    Stream never stops; callback outputs silence when idle.
    This avoids the "first clip works, next clips silent" issue caused by CallbackStop.
    """

    def __init__(self, device: Optional[int] = None, blocksize: int = 256):
        self.device = device
        self.blocksize = blocksize

        self._lock = threading.Lock()
        self._stream: Optional[sd.OutputStream] = None

        self._data: Optional[np.ndarray] = None   # shape (frames, channels)
        self._samplerate: int = 48000
        self._channels: int = 1
        self._pos: int = 0

        # token increments every play/stop; callback checks it for interrupt
        self._token: int = 0
        self._active: bool = False

        self._finished_event = threading.Event()
        self._finished_event.set()

    # ---------- internal ----------
    def _ensure_stream(self, samplerate: int, channels: int):
        need_new = False
        if self._stream is None:
            need_new = True
        else:
            try:
                if int(self._stream.samplerate) != int(samplerate):
                    need_new = True
                if int(self._stream.channels) != int(channels):
                    need_new = True
            except Exception:
                need_new = True

        if not need_new:
            return

        # Close old stream
        if self._stream is not None:
            try:
                self._stream.abort()
            except Exception:
                pass
            try:
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        def callback(outdata, frames, time, status):  # noqa: ARG001
            # snapshot state
            with self._lock:
                token = self._token
                active = self._active
                data = self._data
                pos = self._pos

            if not active or data is None:
                outdata.fill(0)
                return

            end = pos + frames
            chunk = data[pos:end]

            # If interrupted mid-play, immediately silence and mark finished
            with self._lock:
                if token != self._token:
                    self._active = False
                    self._data = None
                    self._pos = 0
                    self._finished_event.set()
                    outdata.fill(0)
                    return

            if chunk.shape[0] < frames:
                # last chunk: pad with zeros and mark finished (DO NOT stop stream!)
                outdata[:chunk.shape[0]] = chunk
                outdata[chunk.shape[0]:].fill(0)

                with self._lock:
                    # ensure token unchanged before marking finished
                    if token == self._token:
                        self._active = False
                        self._data = None
                        self._pos = 0
                        self._finished_event.set()
                return

            outdata[:] = chunk

            with self._lock:
                # advance if token unchanged
                if token == self._token:
                    self._pos = end
                else:
                    # interrupted right after writing
                    self._active = False
                    self._data = None
                    self._pos = 0
                    self._finished_event.set()

        self._stream = sd.OutputStream(
            samplerate=samplerate,
            channels=channels,
            callback=callback,
            device=self.device,
            blocksize=self.blocksize,
        )
        self._stream.start()  # keep stream running always

    # ---------- public ----------
    def play(self, wav_bytes: bytes):
        data, samplerate = sf.read(io.BytesIO(wav_bytes), dtype="float32")
        if data.ndim == 1:
            data = data[:, None]
        channels = data.shape[1]

        with self._lock:
            # new playback token interrupts previous instantly
            self._token += 1
            self._data = data
            self._samplerate = int(samplerate)
            self._channels = int(channels)
            self._pos = 0
            self._active = True
            self._finished_event.clear()

        self._ensure_stream(self._samplerate, self._channels)

    def stop(self):
        with self._lock:
            self._token += 1
            self._active = False
            self._data = None
            self._pos = 0
            self._finished_event.set()

    def is_playing(self) -> bool:
        with self._lock:
            return self._active

    def wait(self, timeout: Optional[float] = None) -> bool:
        return self._finished_event.wait(timeout=timeout)

    def play_and_wait(self, wav_bytes: bytes):
        self.play(wav_bytes)
        self.wait()

    def close(self):
        self.stop()
        if self._stream is not None:
            try:
                self._stream.abort()
            except Exception:
                pass
            try:
                self._stream.close()
            except Exception:
                pass
            self._stream = None
