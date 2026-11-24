"""OS-level typing into whatever window has focus."""
import platform


def type_text(text: str) -> None:
    import pyautogui

    if text.isascii():
        pyautogui.write(text, interval=0.01)
        return
    # non-ASCII (accents, other scripts): paste via clipboard
    import pyperclip

    pyperclip.copy(text)
    pyautogui.hotkey("command" if platform.system() == "Darwin" else "ctrl", "v")
