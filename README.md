# AId

A tiny, free, fully local AI helper that sits in the corner of your screen and helps people who struggle with computers, such as elderly users, immigrants, or anyone who just wants plain answers. It works on Windows, macOS and Linux, needs no account, and sends nothing over the internet after the first model download.

## The idea

Simple is the most important feature. The whole app is one small always-on-top window with a few big buttons: type a question or press Talk and speak it, read the answer or hear it read aloud, and press "Type it for me" to have AId type the answer into whatever window you click on next. Everything runs on your own machine: the language model, speech-to-text and text-to-speech.

## Two modes

The first draft is the normal mode, a plain built-in local language model that answers questions in text or voice.

The beta mode is Screen mode, a checkbox at the bottom. Turning it on swaps the model for one that can see images and adds a single button, "Send my screen to AId". Pressing it hides the window, takes a screenshot of the main monitor, and sends it to the model together with whatever you typed or said.

## Why two different models

A vision-language model can also do plain text, so a single vision model could do everything. But at the same memory budget a text-only model is a little stronger at language, and a vision model also spends memory on its image encoder and on image tokens. Since accuracy matters more than speed here, normal mode uses the biggest text-only model that fits, and Screen mode uses the biggest vision model that fits. Switching modes unloads one and loads the other, so memory is never doubled.

## Picking a model for your hardware

On start AId checks your free RAM and, if you have one, your GPU memory (NVIDIA VRAM, or about 70 percent of unified memory on Apple Silicon). It then walks a ladder of models from largest to smallest and takes the first one that fits, keeping a few GB free for the system and the speech models. If a model fails to download or load, it steps down to the next one automatically. Speed is never a factor: a big model on a slow CPU is still chosen over a small fast one.

Text ladder: Qwen2.5 72B, 32B, 14B, 7B, 3B, 1.5B. Vision ladder: Qwen2.5-VL 32B, 7B, 3B. All are 4-bit GGUF files run through llama.cpp, downloaded once from Hugging Face. Speech-to-text is faster-whisper, multilingual, sized from base to large-v3 by your RAM. Text-to-speech uses your operating system's built-in voices through pyttsx3.

## Download (easiest)

Grab the file for your OS from the GitHub Releases page and open it. No Python, no install.

- Windows: `AId.exe`
- macOS (Apple Silicon): `AId-macos.zip`, unzip, right-click AId.app, Open (first time only, since it is unsigned)
- Linux: `AId`, then `chmod +x AId && ./AId` (needs `espeak-ng` and `libportaudio2` for voice)

Release builds are CPU-only on Windows and Linux; macOS uses Metal. For NVIDIA GPU speed, run from source with a CUDA build (below).

To make a release: push a tag like `v0.1.0`, and GitHub Actions builds all three files. To build locally: `pip install pyinstaller && python build.py`, output in `dist/`.

## Running from source

You need Python 3.10 or newer.

```
pip install -r requirements.txt
python main.py
```

The first launch downloads the model, which can be several gigabytes, and the status line at the top of the window shows progress. Later launches start straight away.

For GPU speed, install a GPU build of llama-cpp-python before the requirements, for example `CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python` for NVIDIA. On Apple Silicon the default build already uses Metal. Without a GPU build, AId runs on CPU only and sizes the model to your RAM.

Platform notes: on Linux, install `espeak-ng` and `libportaudio2` for voice, and note that typing and screenshots need an X11 session, since Wayland blocks both. On macOS, grant Screen Recording, Accessibility and Microphone permission to your terminal or the packaged app when asked.

## Layout

```
main.py          entry point
aid/hardware.py  detects RAM and GPU memory
aid/models.py    model ladders and the picker
aid/llm.py       llama.cpp loading, fallback, streaming chat
aid/stt.py       microphone capture and faster-whisper
aid/tts.py       speaking answers aloud
aid/screen.py    screenshot to image for the vision model
aid/control.py   typing into the focused window
aid/ui.py        the small window
```

## Status and limits

This is a first draft and has not yet been tested on all three operating systems. "Type it for me" types the last answer after a four-second countdown so you can click the target field; it does not yet control the mouse or act on its own. Packaging into a one-click installer is a later step. Everything used is free and open source.
