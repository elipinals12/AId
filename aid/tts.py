"""Local text-to-speech using the operating system's own voices (pyttsx3)."""
import re
import threading


class TTS:
    def __init__(self):
        self.engine = None
        self.lock = threading.Lock()

    def speak(self, text: str) -> None:
        text = re.sub(r"[*_`#]+", "", text)
        threading.Thread(target=self._run, args=(text,), daemon=True).start()

    def _run(self, text: str) -> None:
        with self.lock:
            try:
                import pyttsx3

                self.engine = pyttsx3.init()
                self.engine.setProperty("rate", 150)
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception:
                pass
            finally:
                self.engine = None

    def stop(self) -> None:
        try:
            if self.engine:
                self.engine.stop()
        except Exception:
            pass
