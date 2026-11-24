"""Local speech-to-text: faster-whisper (multilingual) + sounddevice mic capture."""
from typing import Callable

import numpy as np

from .hardware import Hardware
from .models import whisper_size

RATE = 16000


class STT:
    def __init__(self, hw: Hardware, status: Callable[[str], None]):
        self.hw, self.status = hw, status
        self.model = None
        self.stream = None
        self.frames: list = []

    def start(self) -> None:
        import sounddevice as sd

        self.frames = []
        self.stream = sd.InputStream(
            samplerate=RATE, channels=1, dtype="float32",
            callback=lambda data, *_: self.frames.append(data.copy()),
        )
        self.stream.start()

    def stop_and_transcribe(self) -> str:
        self.stream.stop()
        self.stream.close()
        self.stream = None
        if not self.frames:
            return ""
        audio = np.concatenate(self.frames).flatten()
        if self.model is None:
            from faster_whisper import WhisperModel

            size = whisper_size(self.hw)
            self.status(f"Loading speech model ({size})...")
            self.model = WhisperModel(size, device="cpu", compute_type="int8")
        segments, _ = self.model.transcribe(audio, beam_size=5, vad_filter=True)
        return " ".join(s.text.strip() for s in segments).strip()
