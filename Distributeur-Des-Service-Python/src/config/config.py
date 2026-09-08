import json
import os
from dotenv import load_dotenv

# Force le chargement du fichier .env
load_dotenv(override=True)


def _build_tts_voice_map() -> dict:
    """Voix neuronales Azure par défaut selon locale (BCP‑47 ou code court). À surcharger avec AZURE_TTS_VOICE_BY_LOCALE (JSON)."""
    defaults = {
        "ar-sa": "ar-SA-HamedNeural",
        "ar": "ar-SA-HamedNeural",
        "fr-fr": "fr-FR-HenriNeural",
        "fr": "fr-FR-HenriNeural",
        "en-us": "en-US-GuyNeural",
        "en-gb": "en-GB-RyanNeural",
        "en": "en-US-GuyNeural",
    }
    raw = os.getenv("AZURE_TTS_VOICE_BY_LOCALE", "").strip()
    if not raw:
        return defaults
    try:
        custom = json.loads(raw)
        for k, v in custom.items():
            if isinstance(k, str) and isinstance(v, str) and k.strip():
                defaults[k.strip().lower()] = v.strip()
    except json.JSONDecodeError:
        pass
    return defaults


def _env_bool(key: str, default: bool = False) -> bool:
    raw = os.getenv(key)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


class Settings:
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
    AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")
    AZURE_SPEECH_VOICE = os.getenv("AZURE_SPEECH_VOICE", "ar-SA-HamedNeural")
    AZURE_SPEECH_RECOGNITION_LANGUAGE = os.getenv("AZURE_SPEECH_RECOGNITION_LANGUAGE", "ar-SA")
    # TTS « robot compagnon » (SSML prosody — style proche EMO / petit robot)
    AZURE_TTS_ROBOT_EFFECT = _env_bool("AZURE_TTS_ROBOT_EFFECT", True)
    AZURE_TTS_ROBOT_PITCH = os.getenv("AZURE_TTS_ROBOT_PITCH", "+28%")
    AZURE_TTS_ROBOT_RATE = os.getenv("AZURE_TTS_ROBOT_RATE", "1.12")
    AZURE_TTS_ROBOT_VOLUME = os.getenv("AZURE_TTS_ROBOT_VOLUME", "").strip() or None

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    GEMINI_TIMEOUT_SECONDS = int(os.getenv("GEMINI_TIMEOUT_SECONDS", "60"))
    GEMINI_MAX_RETRIES = int(os.getenv("GEMINI_MAX_RETRIES", "3"))

    FFMPEG_PATH = os.getenv("FFMPEG_PATH")
    # Colonne date agenda en base (schéma : date_modifiction)
    SUPABASE_AGENDA_DATE_COLUMN = os.getenv("SUPABASE_AGENDA_DATE_COLUMN", "date_modifiction")

    # Déclencheur nocturne : webhook n8n par utilisateur (00:00 par défaut)
    NIGHTLY_USER_WEBHOOK_URL = os.getenv(
        "NIGHTLY_USER_WEBHOOK_URL",
        "http://localhost:5678/webhook/60fca303-14f2-4922-ab8e-764566b57e85",
    )
    NIGHTLY_USER_TRIGGER_ENABLED = _env_bool("NIGHTLY_USER_TRIGGER_ENABLED", True)
    NIGHTLY_TRIGGER_HOUR = int(os.getenv("NIGHTLY_TRIGGER_HOUR", "0"))
    NIGHTLY_TRIGGER_MINUTE = int(os.getenv("NIGHTLY_TRIGGER_MINUTE", "0"))
    NIGHTLY_USER_WEBHOOK_TIMEOUT_S = float(os.getenv("NIGHTLY_USER_WEBHOOK_TIMEOUT_S", "30"))


_TTS_VOICE_MAP = _build_tts_voice_map()

settings = Settings()


def resolve_tts_voice_for_bcp47_locale(locale: str, fallback_voice: str) -> str:
    """Retourne la voix Neural Azure correspondant à la langue/locale du robot (audio finale = même langue que setting.langue)."""
    if not locale or not locale.strip():
        return fallback_voice
    key_full = locale.strip().lower()
    if key_full in _TTS_VOICE_MAP:
        return _TTS_VOICE_MAP[key_full]
    primary = key_full.split("-")[0]
    if primary in _TTS_VOICE_MAP:
        return _TTS_VOICE_MAP[primary]
    return fallback_voice


if not settings.SUPABASE_URL:
    print("❌ Erreur : SUPABASE_URL est introuvable dans les variables d'environnement")
