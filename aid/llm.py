"""Local LLM via llama.cpp. Text mode and (beta) screen/vision mode."""
import gc
from typing import Callable, Iterator, Optional

from huggingface_hub import hf_hub_download

from .hardware import Hardware
from .models import Model, plan

SYSTEM_PROMPT = (
    "You are AId, a patient helper for people who are not comfortable with computers. "
    "Use plain, short sentences and no jargon. Give one step at a time, numbered. "
    "Name buttons and menus exactly as they appear. Reply in the same language the user writes in. "
    "If you are unsure, say so instead of guessing."
)


class LLM:
    def __init__(self, hw: Hardware, vision: bool, status: Callable[[str], None]):
        self.hw, self.vision, self.status = hw, vision, status
        self.llm = None
        self.model: Optional[Model] = None

    def load(self) -> None:
        from llama_cpp import Llama

        last_err = None
        for model, ngl in plan(self.hw, self.vision):
            try:
                self.status(f"Downloading {model.name} (first time only)...")
                path = hf_hub_download(model.repo, model.file)
                handler = None
                if model.vision:
                    from llama_cpp.llama_chat_format import Qwen25VLChatHandler

                    handler = Qwen25VLChatHandler(
                        clip_model_path=hf_hub_download(model.repo, model.mmproj)
                    )
                self.status(f"Loading {model.name}...")
                self.llm = Llama(
                    model_path=path,
                    chat_handler=handler,
                    n_ctx=8192,
                    n_gpu_layers=ngl,
                    n_threads=self.hw.threads,
                    verbose=False,
                )
                self.model = model
                self.status(f"Ready ({model.name}, {'GPU' if ngl else 'CPU'})")
                return
            except Exception as e:  # out of memory, missing handler, bad download: step down
                last_err = e
                self.llm = None
                gc.collect()
                self.status(f"{model.name} failed, trying smaller...")
        raise RuntimeError(f"No model could be loaded: {last_err}")

    def unload(self) -> None:
        self.llm = None
        self.model = None
        gc.collect()

    def chat(self, history: list[dict], user_text: str, image_uri: Optional[str] = None) -> Iterator[str]:
        content = user_text
        if image_uri:
            content = [
                {"type": "image_url", "image_url": {"url": image_uri}},
                {"type": "text", "text": user_text},
            ]
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, *history, {"role": "user", "content": content}]
        for chunk in self.llm.create_chat_completion(messages=messages, stream=True, temperature=0.3):
            tok = chunk["choices"][0]["delta"].get("content")
            if tok:
                yield tok
