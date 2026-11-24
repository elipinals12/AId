"""Detect how much memory the machine can give to a model."""
import platform
import shutil
import subprocess
from dataclasses import dataclass

import psutil


@dataclass
class Hardware:
    ram_total_gb: float
    ram_free_gb: float
    vram_free_gb: float  # usable GPU memory (NVIDIA VRAM, or ~70% of RAM on Apple Silicon)
    threads: int

    def describe(self) -> str:
        gpu = f", GPU {self.vram_free_gb:.0f} GB" if self.vram_free_gb else ", no GPU"
        return f"{self.ram_total_gb:.0f} GB RAM{gpu}"


def _nvidia_free_gb() -> float:
    if not shutil.which("nvidia-smi"):
        return 0.0
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10,
        ).stdout.split()
        return max(float(x) for x in out) / 1024
    except Exception:
        return 0.0


def _gpu_offload_supported() -> bool:
    try:
        import llama_cpp
        return bool(llama_cpp.llama_supports_gpu_offload())
    except Exception:
        return False


def detect() -> Hardware:
    vm = psutil.virtual_memory()
    total, free = vm.total / 1e9, vm.available / 1e9
    vram = 0.0
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        vram = total * 0.70  # unified memory, Metal limit
    elif _gpu_offload_supported():
        vram = _nvidia_free_gb()
    threads = psutil.cpu_count(logical=False) or psutil.cpu_count() or 4
    return Hardware(total, free, vram, threads)
