from __future__ import annotations

import html
from typing import Optional


def escape_ssml_text(text: str) -> str:
    """Escape user/n8n text for inclusion inside SSML."""
    return html.escape(text or "", quote=False)


def locale_from_voice_name(voice_name: str, fallback: str = "ar-SA") -> str:
    """Derive BCP-47 locale from Azure voice id (e.g. ar-SA-HamedNeural -> ar-SA)."""
    if not voice_name or not voice_name.strip():
        return fallback
    parts = voice_name.strip().split("-")
    if len(parts) >= 2 and len(parts[0]) == 2 and len(parts[1]) == 2:
        return f"{parts[0]}-{parts[1]}"
    return fallback


def build_robot_ssml(
    text: str,
    voice_name: str,
    *,
    xml_lang: Optional[str] = None,
    pitch: str = "+28%",
    rate: str = "1.12",
    volume: Optional[str] = None,
) -> str:
    """
    SSML profile inspired by small companion robots (higher pitch, slightly faster).
    Uses Azure <prosody> on a Neural voice — no extra API keys required.
    """
    lang = xml_lang or locale_from_voice_name(voice_name)
    safe_text = escape_ssml_text(text)
    prosody_attrs = [f'pitch="{pitch}"', f'rate="{rate}"']
    if volume:
        prosody_attrs.append(f'volume="{volume}"')
    prosody_open = " ".join(prosody_attrs)
    return (
        f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
        f'xml:lang="{lang}">'
        f'<voice name="{voice_name}">'
        f"<prosody {prosody_open}>{safe_text}</prosody>"
        f"</voice></speak>"
    )


def is_robot_effect_enabled(raw: Optional[str]) -> bool:
    if raw is None:
        return True
    value = str(raw).strip().lower()
    if not value:
        return True
    return value in ("1", "true", "yes", "on")
