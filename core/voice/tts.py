# core/voice/tts.py — Phase 12: Text-to-Speech (offline, Windows)
# Uses pyttsx3 — no API key, runs locally via Windows SAPI.
# DESIGN RULES:
#   - pyttsx3 is NEVER imported at module level
#   - Each speak() creates a fresh engine in its own daemon thread
#   - engine.stop() is intentionally OMITTED — causes "No attribute endLoop"
#     crash on Windows SAPI when called after runAndWait(). Use del instead.

import re
import threading


def speak(text: str):
    """
    Speak text in a background daemon thread — completely non-blocking.
    Safe to call from inside an async FastAPI route.
    Silently swallows all TTS errors so voice never breaks main flow.
    """
    clean = _clean_text(text)
    if not clean:
        return

    def _run():
        try:
            import pyttsx3          # import inside thread — avoids event loop conflict
            e = pyttsx3.init()
            e.setProperty("rate", 175)     # words per minute (comfortable pace)
            e.setProperty("volume", 0.9)
            e.say(clean)
            e.runAndWait()
            del e                   # DO NOT call e.stop() — crashes Windows SAPI
        except Exception as ex:
            print(f"[TTS] {ex}")    # log but never raise — voice is always optional

    threading.Thread(target=_run, daemon=True).start()


def _clean_text(text: str) -> str:
    """
    Strip markdown, tool tags, code, and control tokens so the TTS
    engine reads clean, natural English sentences.
    """
    # ── Remove technical noise ─────────────────────────────────────────
    text = re.sub(r'\[SCREENSHOT_B64\][^\s]*', '', text)   # base64 image blobs
    text = re.sub(r'\[.*?\]', '', text)                     # [TAGS] [BLOCKED] [ERROR]
    text = re.sub(r'```[\s\S]*?```', '', text)              # ```code blocks```
    text = re.sub(r'`[^`]*`', '', text)                     # `inline code`
    text = re.sub(r'https?://\S+', 'link', text)            # URLs → "link"

    # ── Strip markdown formatting ──────────────────────────────────────
    text = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text)     # **bold** / *italic*
    text = re.sub(r'#{1,6}\s+', '', text)                   # ## headers
    text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)   # > blockquotes
    text = re.sub(r'^[-*+]\s+', '', text, flags=re.MULTILINE)  # bullet lists
    text = re.sub(r'^\d+\.\s+', '', text, flags=re.MULTILINE)  # 1. numbered lists

    # ── Convert structure to natural pauses ───────────────────────────
    text = re.sub(r'\n{2,}', '. ', text)                    # paragraph breaks → pause
    text = re.sub(r'\n', ', ', text)                        # single newlines → comma
    text = re.sub(r'\s{2,}', ' ', text)                     # collapse whitespace

    return text.strip()[:300]                               # 300 chars ≈ ~30s of speech
