"""Small always-on-top window. Big buttons, nothing else."""
import threading
import time
import tkinter as tk

from . import control, hardware
from .llm import LLM
from .screen import capture_data_uri
from .stt import STT
from .tts import TTS

FONT = ("Helvetica", 13)
BIG = ("Helvetica", 14, "bold")


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AId")
        self.root.attributes("-topmost", True)
        w, h = 380, 540
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{sw - w - 20}+{sh - h - 70}")

        self.hw = hardware.detect()
        self.llm = None
        self.stt = STT(self.hw, self.set_status)
        self.tts = TTS()
        self.history: list[dict] = []
        self.last_reply = ""
        self.busy = False
        self.recording = False

        self.speak_var = tk.BooleanVar(value=True)
        self.screen_var = tk.BooleanVar(value=False)
        self._build()
        self.run_bg(lambda: self.switch_model(False))

    # ---------- layout ----------
    def _build(self):
        r = self.root
        self.status = tk.Label(r, text="Starting...", font=("Helvetica", 10), anchor="w", fg="#555")
        self.status.pack(fill="x", padx=8, pady=(6, 0))

        self.log = tk.Text(r, wrap="word", font=FONT, state="disabled", height=14)
        self.log.pack(fill="both", expand=True, padx=8, pady=6)

        row = tk.Frame(r)
        row.pack(fill="x", padx=8)
        self.entry = tk.Entry(row, font=FONT)
        self.entry.pack(side="left", fill="x", expand=True, ipady=6)
        self.entry.bind("<Return>", lambda _e: self.on_send())
        tk.Button(row, text="Send", font=BIG, command=self.on_send).pack(side="left", padx=(6, 0))

        row2 = tk.Frame(r)
        row2.pack(fill="x", padx=8, pady=6)
        self.talk_btn = tk.Button(row2, text="Talk", font=BIG, command=self.on_talk)
        self.talk_btn.pack(side="left", expand=True, fill="x")
        tk.Button(row2, text="Type it for me", font=BIG, command=self.on_type).pack(side="left", expand=True, fill="x", padx=4)
        tk.Button(row2, text="Hush", font=BIG, command=self.tts.stop).pack(side="left", expand=True, fill="x")

        self.screen_btn = tk.Button(r, text="Send my screen to AId", font=BIG, bg="#cfe8ff", command=self.on_screen)
        # shown only in screen mode

        row3 = self.row3 = tk.Frame(r)
        row3.pack(fill="x", padx=8, pady=(0, 6), side="bottom")
        tk.Checkbutton(row3, text="Speak answers", variable=self.speak_var, font=("Helvetica", 11)).pack(side="left")
        tk.Checkbutton(row3, text="Screen mode (beta)", variable=self.screen_var, font=("Helvetica", 11),
                       command=self.on_mode).pack(side="right")

    # ---------- helpers ----------
    def ui(self, fn):
        self.root.after(0, fn)

    def set_status(self, text: str):
        self.ui(lambda: self.status.config(text=text))

    def append(self, text: str):
        self.log.config(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.config(state="disabled")

    def run_bg(self, fn):
        threading.Thread(target=fn, daemon=True).start()

    # ---------- model switching ----------
    def switch_model(self, vision: bool):
        self.busy = True
        if self.llm:
            self.llm.unload()
        try:
            self.llm = LLM(self.hw, vision, self.set_status)
            self.llm.load()
        except Exception as e:
            self.set_status(f"Error: {e}")
        self.busy = False

    def on_mode(self):
        on = self.screen_var.get()
        if on:
            self.screen_btn.pack(fill="x", padx=8, pady=(0, 6), before=self.row3)
        else:
            self.screen_btn.pack_forget()
        self.history.clear()
        self.run_bg(lambda: self.switch_model(on))

    # ---------- actions ----------
    def on_send(self):
        text = self.entry.get().strip()
        if text:
            self.entry.delete(0, "end")
            self.ask(text, with_screen=False)

    def on_screen(self):
        text = self.entry.get().strip() or "What is on my screen? Tell me simply what to do next."
        self.entry.delete(0, "end")
        self.ask(text, with_screen=True)

    def ask(self, text: str, with_screen: bool):
        if self.busy or not (self.llm and self.llm.llm):
            self.set_status("Please wait, still busy...")
            return
        self.busy = True
        self.append(f"\nYou: {text}\n\nAId: ")
        self.run_bg(lambda: self._answer(text, with_screen))

    def _answer(self, text: str, with_screen: bool):
        try:
            uri = None
            if with_screen:
                self.ui(self.root.withdraw)  # hide ourselves so we are not in the shot
                time.sleep(0.5)
                uri = capture_data_uri()
                self.ui(self.root.deiconify)
            self.set_status("Thinking...")
            reply = ""
            for tok in self.llm.chat(self.history[-12:], text, uri):
                reply += tok
                self.ui(lambda t=tok: self.append(t))
            self.history += [{"role": "user", "content": text}, {"role": "assistant", "content": reply}]
            self.last_reply = reply
            self.ui(lambda: self.append("\n"))
            if self.speak_var.get():
                self.tts.speak(reply)
            self.set_status(f"Ready ({self.llm.model.name})")
        except Exception as e:
            self.ui(self.root.deiconify)
            self.set_status(f"Error: {e}")
        finally:
            self.busy = False

    def on_talk(self):
        if not self.recording:
            try:
                self.stt.start()
            except Exception as e:
                self.set_status(f"Microphone error: {e}")
                return
            self.recording = True
            self.talk_btn.config(text="Done talking", bg="#ffb3b3")
            self.set_status("Listening...")
        else:
            self.recording = False
            self.talk_btn.config(text="Talk", bg=self.root.cget("bg"))
            self.set_status("Understanding you...")
            self.run_bg(self._transcribe)

    def _transcribe(self):
        try:
            text = self.stt.stop_and_transcribe()
        except Exception as e:
            self.set_status(f"Speech error: {e}")
            return
        if text:
            self.ui(lambda: self.ask(text, with_screen=self.screen_var.get()))
        else:
            self.set_status("Didn't hear anything.")

    def on_type(self):
        if not self.last_reply:
            return
        self._countdown(4)

    def _countdown(self, n: int):
        if n > 0:
            self.set_status(f"Click where I should type... {n}")
            self.root.after(1000, lambda: self._countdown(n - 1))
        else:
            self.set_status("Typing...")
            self.run_bg(self._type)

    def _type(self):
        try:
            control.type_text(self.last_reply)
            self.set_status("Typed.")
        except Exception as e:
            self.set_status(f"Typing error: {e}")


def run():
    App().root.mainloop()
