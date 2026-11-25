"""Build a single-file AId executable for the current OS: python build.py"""
import platform

import PyInstaller.__main__

system = platform.system()
args = [
    "main.py",
    "--name=AId",
    "--onefile",
    "--noconfirm",
    "--clean",
    # native libs + data files these packages load at runtime
    "--collect-all=llama_cpp",
    "--collect-all=faster_whisper",
    "--collect-all=ctranslate2",
    "--collect-all=sounddevice",
    "--collect-submodules=pyttsx3",
    "--hidden-import=llama_cpp.llama_chat_format",
    "--hidden-import=PIL._tkinter_finder",
]
if system != "Linux":
    args.append("--windowed")  # no console window on Win/Mac
if system == "Darwin":
    args.append("--osx-bundle-identifier=org.aid.helper")

PyInstaller.__main__.run(args)
