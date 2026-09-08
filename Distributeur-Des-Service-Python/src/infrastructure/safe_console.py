import sys


def safe_console_line(message: str) -> None:
    """Écrit sur stdout en UTF-8 (évite UnicodeEncodeError / charmap sous Windows CMD)."""
    buf = getattr(sys.stdout, "buffer", None)
    if buf is not None:
        try:
            buf.write(message.encode("utf-8", errors="replace"))
            buf.write(b"\n")
            return
        except Exception:
            pass
    try:
        print(message.encode("ascii", errors="replace").decode("ascii"))
    except Exception:
        pass
