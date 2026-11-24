"""Model catalog and the 'biggest that fits' picker. Accuracy over speed."""
from dataclasses import dataclass
from typing import Optional

from .hardware import Hardware

RESERVE_GB = 3.0  # kept free for OS + speech models when running on CPU


@dataclass(frozen=True)
class Model:
    name: str
    repo: str
    file: str
    size_gb: float
    mmproj: Optional[str] = None  # vision projector file, same repo
    mmproj_gb: float = 0.0

    @property
    def vision(self) -> bool:
        return self.mmproj is not None

    @property
    def need_gb(self) -> float:
        # weights + projector, 15% overhead, plus room for context / image tokens
        return (self.size_gb + self.mmproj_gb) * 1.15 + (2.5 if self.vision else 1.0)


# All Q4_K_M GGUF quants, Apache-2.0 / Qwen licence, best first.
TEXT = [
    Model("Qwen2.5 72B", "bartowski/Qwen2.5-72B-Instruct-GGUF", "Qwen2.5-72B-Instruct-Q4_K_M.gguf", 47.4),
    Model("Qwen2.5 32B", "bartowski/Qwen2.5-32B-Instruct-GGUF", "Qwen2.5-32B-Instruct-Q4_K_M.gguf", 19.9),
    Model("Qwen2.5 14B", "bartowski/Qwen2.5-14B-Instruct-GGUF", "Qwen2.5-14B-Instruct-Q4_K_M.gguf", 9.0),
    Model("Qwen2.5 7B", "bartowski/Qwen2.5-7B-Instruct-GGUF", "Qwen2.5-7B-Instruct-Q4_K_M.gguf", 4.7),
    Model("Qwen2.5 3B", "bartowski/Qwen2.5-3B-Instruct-GGUF", "Qwen2.5-3B-Instruct-Q4_K_M.gguf", 1.9),
    Model("Qwen2.5 1.5B", "bartowski/Qwen2.5-1.5B-Instruct-GGUF", "Qwen2.5-1.5B-Instruct-Q4_K_M.gguf", 1.0),
]

VISION = [
    Model("Qwen2.5-VL 32B", "unsloth/Qwen2.5-VL-32B-Instruct-GGUF", "Qwen2.5-VL-32B-Instruct-Q4_K_M.gguf", 19.9, "mmproj-F16.gguf", 1.4),
    Model("Qwen2.5-VL 7B", "unsloth/Qwen2.5-VL-7B-Instruct-GGUF", "Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf", 4.7, "mmproj-F16.gguf", 1.4),
    Model("Qwen2.5-VL 3B", "unsloth/Qwen2.5-VL-3B-Instruct-GGUF", "Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf", 1.9, "mmproj-F16.gguf", 1.4),
]


def plan(hw: Hardware, vision: bool) -> list[tuple[Model, int]]:
    """Return [(model, n_gpu_layers)] best-first. Loader walks the list until one works."""
    catalog = VISION if vision else TEXT
    cpu_budget = hw.ram_free_gb - RESERVE_GB
    out = []
    for m in catalog:
        if m.need_gb <= hw.vram_free_gb:
            out.append((m, -1))  # all layers on GPU
        elif m.need_gb <= cpu_budget:
            out.append((m, 0))  # CPU
    if not out:
        out.append((catalog[-1], 0))  # last resort: smallest, even if tight
    return out


def whisper_size(hw: Hardware) -> str:
    if hw.ram_total_gb >= 48:
        return "large-v3"
    if hw.ram_total_gb >= 16:
        return "medium"
    if hw.ram_total_gb >= 8:
        return "small"
    return "base"
