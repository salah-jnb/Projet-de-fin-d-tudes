import hashlib
import io
import os
import secrets
import shutil
import subprocess
import tempfile
from pathlib import Path
import wave
import httpx
import json
from datetime import datetime
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional
from src.presentation.services_interfaces import IApiService
from src.infrastructure.database import get_supabase_client
from src.infrastructure.n8n_client import N8NClient
from src.infrastructure.safe_console import safe_console_line
from src.infrastructure.free_translate_client import FreeTranslateClient
from src.infrastructure.gemini_client import GeminiClient
from src.config.config import resolve_tts_voice_for_bcp47_locale, settings
from src.infrastructure.tts_robot_ssml import build_robot_ssml, locale_from_voice_name

try:
    import azure.cognitiveservices.speech as speechsdk
    AZURE_SPEECH_AVAILABLE = True
except ImportError:
    AZURE_SPEECH_AVAILABLE = False

try:
    import face_recognition
    import numpy as np
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False


class ApiServiceImpl(IApiService):
    def __init__(self):
        self.client = get_supabase_client()
        self.n8n = N8NClient()
        self.gemini = GeminiClient()
        self.translator = FreeTranslateClient()
        self._known_faces_cache = []
        self._known_faces_cache_at = 0.0
        self._known_faces_ttl_seconds = 300
        self._cache_lock = threading.Lock()
        self._is_refreshing_faces = False

    # --- UTILISATEURS ---
    def get_all_users(self):
        return self.client.table("utilisateur").select("*").execute().data

    def get_user(self, iduser: int):
        res = self.client.table("utilisateur").select("*").eq("iduser", iduser).execute().data
        return res[0] if res else None

    def create_user(self, data: dict):
        return self.client.table("utilisateur").insert(data).execute().data

    def update_user(self, iduser: int, data: dict):
        return self.client.table("utilisateur").update(data).eq("iduser", iduser).execute().data

    def delete_user(self, iduser: int):
        return self.client.table("utilisateur").delete().eq("iduser", iduser).execute().data

    # --- IMAGES UTILISATEUR (table imageuser) ---
    def get_all_user_images(self):
        return self.client.table("imageuser").select("*").execute().data

    def get_user_image(self, idimage: int):
        res = self.client.table("imageuser").select("*").eq("idimage", idimage).execute().data
        return res[0] if res else None

    def get_user_images_by_user(self, iduser: int):
        return self.client.table("imageuser").select("*").eq("iduser", iduser).execute().data

    def create_user_image(self, data: dict):
        row = self.client.table("imageuser").insert(self._fix_booleans(data)).execute().data
        self._invalidate_known_faces_cache()
        return row

    def update_user_image(self, idimage: int, data: dict):
        row = self.client.table("imageuser").update(self._fix_booleans(data)).eq("idimage", idimage).execute().data
        self._invalidate_known_faces_cache()
        return row

    def delete_user_image(self, idimage: int):
        row = self.client.table("imageuser").delete().eq("idimage", idimage).execute().data
        self._invalidate_known_faces_cache()
        return row

    # --- HISTORIQUE ---
    def get_all_history(self):
        return self.client.table("historique").select("*").order("created_at", desc=True).execute().data

    def get_historique(self, historique_id: int):
        res = self.client.table("historique").select("*").eq("id", historique_id).execute().data
        return res[0] if res else None

    def create_historique(self, data: dict):
        return self.client.table("historique").insert(self._fix_booleans(data)).execute().data

    def delete_historique(self, historique_id: int):
        return self.client.table("historique").delete().eq("id", historique_id).execute().data

    # --- CONVERSATIONS ---
    def get_last_100_conversations(self):
        return self.client.table("conversation").select("*").order("date", desc=True).limit(100).execute().data

    def get_all_conversations(self):
        return self.client.table("conversation").select("*").order("date", desc=True).execute().data

    def get_conversation(self, conversation_id: int):
        res = self.client.table("conversation").select("*").eq("id", conversation_id).execute().data
        return res[0] if res else None

    def create_conversation(self, data: dict):
        return self.client.table("conversation").insert(self._fix_booleans(data)).execute().data

    def update_conversation(self, conversation_id: int, data: dict):
        return self.client.table("conversation").update(self._fix_booleans(data)).eq("id", conversation_id).execute().data

    def delete_conversation(self, conversation_id: int):
        return self.client.table("conversation").delete().eq("id", conversation_id).execute().data

    # --- NOTES ---
    def get_all_notes(self):
        return self.client.table("note").select("*").order("id", desc=True).execute().data

    def get_note(self, note_id: int):
        res = self.client.table("note").select("*").eq("id", note_id).execute().data
        return res[0] if res else None

    def create_note(self, data: dict):
        return self.client.table("note").insert(self._fix_booleans(data)).execute().data

    def update_note(self, note_id: int, data: dict):
        return self.client.table("note").update(self._fix_booleans(data)).eq("id", note_id).execute().data

    def delete_note(self, note_id: int):
        return self.client.table("note").delete().eq("id", note_id).execute().data

    def modify_note_etat(self, note_id: int, etat: bool):
        val = 1 if etat else 0
        return self.client.table("note").update({"etat": val}).eq("id", note_id).execute().data

    # --- SETTINGS ---
    # The `setting` table in Supabase uses `idkoda` (UUID) as primary key,
    # NOT `id`. There is exactly one row per robot (single-tenant install).
    def _primary_setting_key(self) -> Optional[str]:
        """Renvoie l'identifiant `idkoda` de l'unique ligne `setting`."""
        res = self.client.table("setting").select("idkoda").limit(1).execute().data
        if not res:
            return None
        v = res[0].get("idkoda")
        return str(v) if v is not None else None

    def get_settings(self):
        res = self.client.table("setting").select("*").limit(1).execute().data
        return res[0] if res else None

    def modify_settings(self, settings_data: dict):
        fixed_data = self._fix_booleans(settings_data)
        # Never let the client overwrite the primary key.
        fixed_data.pop("idkoda", None)
        if not fixed_data:
            return None
        sid = self._primary_setting_key()
        if sid is None:
            return None
        result = (
            self.client.table("setting")
            .update(fixed_data)
            .eq("idkoda", sid)
            .execute()
            .data
        )
        # New values must be visible to the next voice turn — drop the cache.
        self._invalidate_setting_cache()
        return result

    # In-memory cache for setting.* reads: every voice turn calls these and a
    # Supabase round-trip is 80-300 ms (LAN to Supabase + REST). 60 s TTL is
    # long enough to cut ~250 ms per turn, short enough that the MAUI app's
    # PUT /settings is reflected within a minute.
    _SETTING_CACHE_TTL_S = 60.0

    def _setting_cached(self, column: str):
        """Return ``setting.<column>`` from cache (or fetch + cache)."""
        if not hasattr(self, "_setting_cache"):
            self._setting_cache: dict = {}
            self._setting_cache_at: dict = {}
        now = time.time()
        cached_at = self._setting_cache_at.get(column, 0.0)
        if (now - cached_at) < self._SETTING_CACHE_TTL_S and column in self._setting_cache:
            return self._setting_cache[column]
        try:
            res = self.client.table("setting").select(column).limit(1).execute().data
        except Exception:
            return self._setting_cache.get(column)  # stale > nothing on failure
        val = res[0].get(column) if res else None
        self._setting_cache[column] = val
        self._setting_cache_at[column] = now
        return val

    def _invalidate_setting_cache(self) -> None:
        """Called from modify_settings so the next read picks the new values."""
        if hasattr(self, "_setting_cache_at"):
            self._setting_cache_at.clear()

    def _get_robot_langue_from_setting(self):
        """Locale BCP‑47 ou identifiant de langue (ex. ar-SA, fr-FR) stockée dans setting.langue."""
        val = self._setting_cached("langue")
        if val is None:
            return None
        s = str(val).strip()
        return s if s else None

    @staticmethod
    def _canonical_locale_for_speech_and_translation(raw: Optional[str]) -> str:
        """
        Azure Speech STT attend une locale BCP-47 (ex. ar-SA), pas un nom de voix TTS (ex. ar-SA-HamedNeural).
        Erreur 1007 / language invalide si la colonne langue contient une voix Neural.
        """
        fb = settings.AZURE_SPEECH_RECOGNITION_LANGUAGE
        if not raw or not str(raw).strip():
            return fb
        parts = [p for p in str(raw).strip().replace("_", "-").split("-") if p]
        if not parts:
            return fb
        if len(parts) >= 3 and parts[-1].lower().endswith("neural"):
            return f"{parts[0].lower()}-{parts[1].upper()}"
        if len(parts) == 2 and len(parts[0]) >= 2 and len(parts[1]) >= 2:
            return f"{parts[0].lower()}-{parts[1].upper()}"
        if len(parts) == 1 and len(parts[0]) == 2:
            short = parts[0].lower()
            default_region = {"ar": "ar-SA", "fr": "fr-FR", "en": "en-US", "es": "es-ES"}
            return default_region.get(short, fb)
        return fb

    # --- INFOS PERSONNELLES ---
    def get_personal_info(self):
        return self.client.table("information_personelle").select("*").execute().data

    def get_personal_info_by_user(self, iduser: int):
        return self.client.table("information_personelle").select("*").eq("iduser", iduser).execute().data

    def add_personal_info(self, info_data: dict):
        return self.client.table("information_personelle").insert(self._fix_booleans(info_data)).execute().data

    def update_personal_info(self, info_id: int, data: dict):
        return self.client.table("information_personelle").update(self._fix_booleans(data)).eq("id", info_id).execute().data

    def delete_personal_info(self, info_id: int):
        return self.client.table("information_personelle").delete().eq("id", info_id).execute().data

    # --- ACCOMPAGNEMENT ---
    def get_all_accompagnements(self):
        return self.client.table("accompagnement").select("*").order("id", desc=True).execute().data

    def get_accompagnement(self, accompagnement_id: int):
        res = self.client.table("accompagnement").select("*").eq("id", accompagnement_id).execute().data
        return res[0] if res else None

    def get_accompagnements_by_user(self, iduser: int):
        return self.client.table("accompagnement").select("*").eq("iduser", iduser).execute().data

    def create_accompagnement(self, data: dict):
        return self.client.table("accompagnement").insert(self._fix_booleans(data)).execute().data

    def update_accompagnement(self, accompagnement_id: int, data: dict):
        return self.client.table("accompagnement").update(self._fix_booleans(data)).eq("id", accompagnement_id).execute().data

    def delete_accompagnement(self, accompagnement_id: int):
        return self.client.table("accompagnement").delete().eq("id", accompagnement_id).execute().data

    # --- AUTHENTIFICATION ---
    def login(self, emailclient: str, motdepasse: str):
        res = (
            self.client.table("authentification")
            .select("*")
            .eq("emailclient", emailclient)
            .limit(1)
            .execute()
            .data
        )
        if not res:
            return None
        row = res[0]
        stored = str(row.get("motdepasse", ""))
        if not secrets.compare_digest(stored, str(motdepasse)):
            return None
        return {
            "idproduit": row.get("idproduit"),
            "emailclient": row.get("emailclient"),
            "idkoda": row.get("idkoda"),
        }

    def get_authentification(self, idproduit: int):
        res = self.client.table("authentification").select("*").eq("idproduit", idproduit).execute().data
        return res[0] if res else None

    def list_authentifications(self):
        return self.client.table("authentification").select("*").execute().data

    def create_authentification(self, data: dict):
        return self.client.table("authentification").insert(self._fix_booleans(data)).execute().data

    def update_authentification(self, idproduit: int, data: dict):
        return self.client.table("authentification").update(self._fix_booleans(data)).eq("idproduit", idproduit).execute().data

    def delete_authentification(self, idproduit: int):
        return self.client.table("authentification").delete().eq("idproduit", idproduit).execute().data

    def _agenda_db_payload(self, data: dict) -> dict:
        """Mappe date_modification (API) vers le nom de colonne réel en base (ex. date_modifiction)."""
        d = self._fix_booleans(data.copy())
        col = settings.SUPABASE_AGENDA_DATE_COLUMN
        if col and col != "date_modification" and "date_modification" in d:
            d[col] = d.pop("date_modification")
        return d

    # --- INTEGRATION N8N ---
    def send_to_n8n(self, payload: dict):
        """Envoie au webhook n8n un corps avec le champ attendu par le workflow : ``message``."""
        if not isinstance(payload, dict):
            raise TypeError("send_to_n8n attend un dict.")
        if "message" in payload:
            body = {"message": payload["message"]}
        elif "text" in payload:
            body = {"message": payload["text"]}
        else:
            body = payload
        return self.n8n.trigger_workflow(body)

    # =========================================================
    # --- DÉCLENCHEUR NOCTURNE (webhook n8n par utilisateur) ---
    # =========================================================
    def run_nightly_user_webhook_trigger(self) -> dict:
        """
        Récupère tous les utilisateurs (table utilisateur) et appelle le webhook n8n
        une fois par personne, avec le paramètre ``user`` = nom (ex. oussema, salah).
        """
        webhook_url = (settings.NIGHTLY_USER_WEBHOOK_URL or "").strip()
        if not webhook_url:
            raise RuntimeError("NIGHTLY_USER_WEBHOOK_URL non configuré dans le .env")

        timeout_s = settings.NIGHTLY_USER_WEBHOOK_TIMEOUT_S
        users = self.client.table("utilisateur").select("iduser, nom").execute().data or []

        results = []
        for row in users:
            nom = (row.get("nom") or "").strip()
            if not nom:
                results.append({
                    "iduser": row.get("iduser"),
                    "nom": None,
                    "ok": False,
                    "skipped": True,
                    "error": "nom vide",
                })
                continue

            request_url = f"{webhook_url}?user={nom}"
            payload = {"user": nom}
            try:
                safe_console_line(f"[NIGHTLY] → POST {request_url}  payload={payload}")
                response = httpx.post(
                    webhook_url,
                    params={"user": nom},
                    json=payload,
                    timeout=timeout_s,
                )
                ok = response.is_success
                results.append({
                    "iduser": row.get("iduser"),
                    "nom": nom,
                    "ok": ok,
                    "status_code": response.status_code,
                    "request_url": request_url,
                    "response": (response.text or "")[:500],
                })
                safe_console_line(
                    f"[NIGHTLY] ← {nom}: HTTP {response.status_code}"
                )
            except Exception as exc:
                safe_console_line(f"[NIGHTLY] ❌ {nom}: {exc!s}")
                results.append({
                    "iduser": row.get("iduser"),
                    "nom": nom,
                    "ok": False,
                    "request_url": request_url,
                    "error": str(exc),
                })

        success_count = sum(1 for r in results if r.get("ok"))
        skipped_count = sum(1 for r in results if r.get("skipped"))
        return {
            "status": "completed",
            "webhook_url": webhook_url,
            "users_total": len(users),
            "users_processed": len(results) - skipped_count,
            "success_count": success_count,
            "failure_count": len(results) - success_count - skipped_count,
            "skipped_count": skipped_count,
            "results": results,
        }

    # =========================================================
    # --- AGENDA ---
    # =========================================================
    def get_all_agendas(self):
        sort_col = settings.SUPABASE_AGENDA_DATE_COLUMN or "date_modifiction"
        return self.client.table("agenda").select("*").order(sort_col, desc=True).execute().data

    def get_agenda(self, agenda_id: int):
        res = self.client.table("agenda").select("*").eq("id", agenda_id).execute().data
        return res[0] if res else None

    def create_agenda(self, data: dict):
        return self.client.table("agenda").insert(self._agenda_db_payload(data)).execute().data

    def update_agenda(self, agenda_id: int, data: dict):
        return self.client.table("agenda").update(self._agenda_db_payload(data)).eq("id", agenda_id).execute().data

    def delete_agenda(self, agenda_id: int):
        return self.client.table("agenda").delete().eq("id", agenda_id).execute().data

    # =========================================================
    # --- SMART NOTES (Mappé sur la table 'note') ---
    # =========================================================
    def get_all_activities(self):
        # On utilise la table 'note' qui existe déjà
        return self.client.table("note").select("*").order("id", desc=True).execute().data

    def get_activity(self, activity_id: int):
        res = self.client.table("note").select("*").eq("id", activity_id).execute().data
        return res[0] if res else None

    def create_activity(self, data: dict):
        note_text = data.get("note", data.get("description", ""))
        payload = {
            "note": note_text,
            "etat": 1 if data.get("etat", False) else 0,
        }
        if data.get("date") is not None:
            payload["date"] = data["date"]
        return self.client.table("note").insert(self._fix_booleans(payload)).execute().data

    def update_activity(self, activity_id: int, data: dict):
        payload = self._fix_booleans(data.copy())
        if "description" in payload:
            payload["note"] = payload.pop("description")
        return self.client.table("note").update(payload).eq("id", activity_id).execute().data

    def delete_activity(self, activity_id: int):
        return self.client.table("note").delete().eq("id", activity_id).execute().data

    # =========================================================
    # --- RECONNAISSANCE FACIALE ---
    # =========================================================
    def identify_face(self, image_bytes: bytes) -> str:
        if not FACE_RECOGNITION_AVAILABLE:
            raise RuntimeError("La bibliothèque face_recognition n'est pas installée.")

        input_image = face_recognition.load_image_file(io.BytesIO(image_bytes))
        input_image = self._resize_image_for_speed(input_image, max_width=800)
        input_locations = face_recognition.face_locations(input_image, model="hog")
        input_encodings = face_recognition.face_encodings(input_image, known_face_locations=input_locations, num_jitters=1)
        if not input_encodings:
            return "inconnu"

        known_faces = self._get_known_faces()
        if not known_faces:
            return "inconnu"

        known_encodings = [item["encoding"] for item in known_faces]
        best_name = "inconnu"
        best_distance = 1.0
        tolerance = 0.50

        # Compare chaque visage détecté dans l'image d'entrée avec tous les utilisateurs connus.
        for input_encoding in input_encodings:
            distances = face_recognition.face_distance(known_encodings, input_encoding)
            if len(distances) == 0:
                continue
            best_idx = int(np.argmin(distances))
            current_distance = float(distances[best_idx])
            if current_distance < best_distance:
                best_distance = current_distance
                best_name = known_faces[best_idx]["nom"]

        if best_distance <= tolerance:
            return best_name
        return "inconnu"

    # =========================================================
    # --- POWER ON / OFF ---
    # =========================================================
    def power_off(self):
        sid = self._primary_setting_key()
        if sid is not None:
            self.client.table("setting").update({"etat": 0}).eq("idkoda", sid).execute()
        return {"status": "power_off", "etat": 0}

    def power_on(self):
        sid = self._primary_setting_key()
        if sid is not None:
            self.client.table("setting").update({"etat": 1}).eq("idkoda", sid).execute()
        return {"status": "power_on", "etat": 1}

    # =========================================================
    # --- AUDIO (AZURE SPEECH) ---
    # =========================================================
    @staticmethod
    def _closed_push_stream_raw_pcm(pcm_data: bytes, sample_rate: int, channels: int, bits_per_sample: int):
        stream_format = speechsdk.audio.AudioStreamFormat(
            samples_per_second=sample_rate,
            bits_per_sample=bits_per_sample,
            channels=channels,
        )
        push_stream = speechsdk.audio.PushAudioInputStream(stream_format=stream_format)
        push_stream.write(pcm_data)
        push_stream.close()
        return push_stream

    def _resolve_ffmpeg_executable(self):
        """PATH pas encore à jour après winget → essai lien WinGet + FFMPEG_PATH dans .env."""
        if getattr(settings, "FFMPEG_PATH", None):
            configured = Path(settings.FFMPEG_PATH.strip().strip('"'))
            if configured.is_file():
                return str(configured)
        found = shutil.which("ffmpeg")
        if found:
            return found
        local = os.environ.get("LOCALAPPDATA", "")
        if local:
            winget_link = Path(local) / "Microsoft" / "WinGet" / "Links" / "ffmpeg.exe"
            if winget_link.is_file():
                return str(winget_link)
        return None

    def _transcode_to_raw_s16le_mono_16k_via_ffmpeg(self, audio_bytes: bytes):
        """
        Contourne SPXERR_GSTREAMER_NOT_FOUND_ERROR : Azure reçoit uniquement du PCM linéaire brut,
        sans décodeur conteneur côté SDK (pas de GStreamer sous Windows).
        """
        ffmpeg = self._resolve_ffmpeg_executable()
        if not ffmpeg:
            return None
        in_path = out_path = None
        try:
            fd_in, in_path = tempfile.mkstemp(suffix=".bin")
            os.close(fd_in)
            fd_out, out_path = tempfile.mkstemp(suffix=".raw")
            os.close(fd_out)
            with open(in_path, "wb") as f:
                f.write(audio_bytes)
            subprocess.run(
                [
                    ffmpeg,
                    "-nostdin",
                    "-nostats",
                    "-loglevel",
                    "error",
                    "-y",
                    "-i",
                    in_path,
                    "-vn",
                    "-f",
                    "s16le",
                    "-acodec",
                    "pcm_s16le",
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    out_path,
                ],
                check=True,
                timeout=120,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            with open(out_path, "rb") as f:
                return f.read()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError, FileNotFoundError):
            return None
        finally:
            for p in (in_path, out_path):
                if p:
                    try:
                        os.unlink(p)
                    except OSError:
                        pass

    def _try_push_stream_pcm_wav(self, audio_bytes: bytes):
        """
        PCM linéaire 8 ou 16 bits uniquement (évite le WAV float 32 bits pris pour du PCM brut).
        Ne pas utiliser AudioStreamContainerFormat.ANY sur Windows sans GStreamer.
        """
        try:
            buf = io.BytesIO(audio_bytes)
            with wave.open(buf, "rb") as wf:
                if wf.getcomptype() != "NONE":
                    return None
                channels = wf.getnchannels()
                sample_width = wf.getsampwidth()
                sample_rate = wf.getframerate()
                if channels < 1 or sample_width not in (1, 2):
                    return None
                pcm_data = wf.readframes(wf.getnframes())
        except (wave.Error, EOFError):
            return None

        return self._closed_push_stream_raw_pcm(
            pcm_data, sample_rate, channels, sample_width * 8
        )

    def speech_to_text(self, audio_bytes: bytes):
        if not AZURE_SPEECH_AVAILABLE:
            raise RuntimeError("La bibliothèque azure-cognitiveservices-speech n'est pas installée.")
        self._validate_azure_speech_config()

        speech_config = speechsdk.SpeechConfig(
            subscription=settings.AZURE_SPEECH_KEY,
            region=settings.AZURE_SPEECH_REGION
        )
        langue_brute_setting = self._get_robot_langue_from_setting()
        recognition_lang = self._canonical_locale_for_speech_and_translation(
            langue_brute_setting
        )
        safe_console_line("--- Speech-to-Text (service Azure) ---")
        safe_console_line(
            f"Langue lue depuis la table setting.langue : {langue_brute_setting!s}"
        )
        safe_console_line(
            f"Langue utilisee pour la reconnaissance Azure (normalisee) : {recognition_lang}"
        )
        speech_config.speech_recognition_language = recognition_lang

        push_stream = self._try_push_stream_pcm_wav(audio_bytes)
        if push_stream is None:
            raw_pcm = self._transcode_to_raw_s16le_mono_16k_via_ffmpeg(audio_bytes)
            if raw_pcm:
                push_stream = self._closed_push_stream_raw_pcm(raw_pcm, 16000, 1, 16)
        if push_stream is None:
            hint = (
                "FFmpeg introuvable : redémarre le terminal après winget (PATH), ou définit FFMPEG_PATH dans .env "
                "(chemin vers ffmpeg.exe, ex. …\\WinGet\\Links\\ffmpeg.exe), ou exporte un WAV PCM 16 bit. "
                "Réf. erreur SDK : SPXERR_GSTREAMER_NOT_FOUND_ERROR sous Windows sans décodage FFmpeg."
            )
            raise RuntimeError(hint)

        result = None
        audio_config = speechsdk.audio.AudioConfig(stream=push_stream)
        recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
        result = recognizer.recognize_once_async().get()

        if result is None:
            raise RuntimeError("Échec Speech-to-Text (aucun résultat du recognizer).")

        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            safe_console_line(f"Convertir la voix en texte : {result.text.strip()}")
            return {
                "text": result.text,
                "status": "success"
            }

        if result.reason == speechsdk.ResultReason.NoMatch:
            return {
                "text": "",
                "status": "no_match"
            }

        if result.reason == speechsdk.ResultReason.Canceled:
            details = result.cancellation_details
            error_message = f"Erreur de reconnaissance: {details.reason}"
            if details.reason == speechsdk.CancellationReason.Error and details.error_details:
                error_message = f"{error_message} - {details.error_details}"
                if "1007" in details.error_details or "language" in details.error_details.lower():
                    error_message += (
                        " Cause frequente : setting.langue invalide ou nom de voix TTS au lieu "
                        "dune locale Azure (utiliser par ex. ar-SA, pas ar-SA-HamedNeural)."
                    )
            raise RuntimeError(error_message)

        return {
            "text": "",
            "status": "unknown"
        }

    def text_to_speech(self, text: str, voice_name=None):
        if not AZURE_SPEECH_AVAILABLE:
            raise RuntimeError("La bibliothèque azure-cognitiveservices-speech n'est pas installée.")
        self._validate_azure_speech_config()

        chosen_voice = voice_name or settings.AZURE_SPEECH_VOICE
        speech_config = speechsdk.SpeechConfig(
            subscription=settings.AZURE_SPEECH_KEY,
            region=settings.AZURE_SPEECH_REGION
        )
        speech_config.speech_synthesis_voice_name = chosen_voice

        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
        if settings.AZURE_TTS_ROBOT_EFFECT:
            ssml = build_robot_ssml(
                text,
                chosen_voice,
                xml_lang=locale_from_voice_name(
                    chosen_voice, settings.AZURE_SPEECH_RECOGNITION_LANGUAGE
                ),
                pitch=settings.AZURE_TTS_ROBOT_PITCH,
                rate=settings.AZURE_TTS_ROBOT_RATE,
                volume=settings.AZURE_TTS_ROBOT_VOLUME,
            )
            safe_console_line(
                f"TTS mode robot (SSML) voix={chosen_voice} "
                f"pitch={settings.AZURE_TTS_ROBOT_PITCH} rate={settings.AZURE_TTS_ROBOT_RATE}"
            )
            result = synthesizer.speak_ssml_async(ssml).get()
        else:
            result = synthesizer.speak_text_async(text).get()

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            return bytes(result.audio_data)

        if result.reason == speechsdk.ResultReason.Canceled:
            details = result.cancellation_details
            error_message = f"Erreur de synthèse: {details.reason}"
            if details.reason == speechsdk.CancellationReason.Error and details.error_details:
                error_message = f"{error_message} - {details.error_details}"
            raise RuntimeError(error_message)

        raise RuntimeError("La synthèse vocale n'a pas abouti.")

    @staticmethod
    def _bcp47_primary(lang: str) -> str:
        if not lang or not str(lang).strip():
            return "ar"
        return str(lang).strip().split("-")[0].lower()

    def _tts_voice_for_robot_locale(self, robot_bcp47: Optional[str], voice_name=None):
        if voice_name:
            return voice_name
        loc = (robot_bcp47 or "").strip() or settings.AZURE_SPEECH_RECOGNITION_LANGUAGE
        return resolve_tts_voice_for_bcp47_locale(loc, settings.AZURE_SPEECH_VOICE)

    @staticmethod
    def _compose_stt_with_extra_text(stt_text: str, extra_text: Optional[str]) -> str:
        """Forme « question_vocale (texte_libre) » avant traduction / n8n."""
        base = (stt_text or "").strip()
        extra = (str(extra_text).strip() if extra_text else "")
        if not extra:
            return base
        if not base:
            return f"({extra})"
        return f"{base} ({extra})"

    def audio_to_n8n_to_audio(self, audio_bytes: bytes, voice_name=None, extra_text=None):
        safe_console_line("========== Pipeline audio -> n8n -> audio ==========")
        langue_brute = self._get_robot_langue_from_setting()
        robot_lang_setting = self._canonical_locale_for_speech_and_translation(langue_brute)
        robot_tr = self._bcp47_primary(robot_lang_setting)

        safe_console_line(
            f"Langue robot : brut (table setting) = {langue_brute!s} | normalise = {robot_lang_setting}"
        )

        stt_result = self.speech_to_text(audio_bytes)
        input_text = (stt_result or {}).get("text", "").strip()
        safe_console_line(
            f"Statut reconnaissance vocale : {stt_result.get('status') if isinstance(stt_result, dict) else 'unknown'}"
        )
        question_for_n8n = self._compose_stt_with_extra_text(input_text, extra_text)
        if not question_for_n8n:
            safe_console_line("Erreur : aucun texte apres conversion voix -> texte.")
            raise RuntimeError("Aucun texte reconnu depuis l'audio.")
        if not input_text and extra_text and str(extra_text).strip():
            safe_console_line(
                f"STT vide — envoi n8n avec identite seule : {question_for_n8n!r}"
            )
        if extra_text and str(extra_text).strip():
            safe_console_line(f"Texte client a ajouter entre parentheses : {str(extra_text).strip()}")
            safe_console_line(f"Question composee (voix + texte) : {question_for_n8n}")

        if robot_tr == "fr":
            text_fr_for_n8n = question_for_n8n
            safe_console_line(f"Traduire en francais : (deja francais, inchangé) {text_fr_for_n8n}")
        else:
            text_fr_for_n8n = self.translator.translate_text(
                question_for_n8n, robot_lang_setting, "fr-FR"
            )
            safe_console_line(f"Traduire en francais : {text_fr_for_n8n}")

        safe_console_line("Envoi n8n (payload JSON « message » en français).")
        n8n_response = self.send_to_n8n({"message": text_fr_for_n8n})

        reply_fr = self._extract_text_from_n8n_response(n8n_response)
        safe_console_line(f"Resultat brut n8n (objet ou texte brut) : {n8n_response!s}")
        safe_console_line(f"Resultat (texte extrait pour traitement, attendu francais) : {reply_fr}")
        if not reply_fr:
            safe_console_line("Erreur : n8n na pas renvoye de texte exploitable.")
            raise RuntimeError("Le workflow n8n n'a pas retourné de texte exploitable.")

        if robot_tr == "fr":
            reply_robot_lang = reply_fr
            safe_console_line(
                f"Traduction vers langue robot ({robot_lang_setting}) : (inchangé) {reply_robot_lang}"
            )
        else:
            reply_robot_lang = self.translator.translate_text(reply_fr, "fr-FR", robot_lang_setting)
            safe_console_line(
                f"Traduction vers langue robot ({robot_lang_setting}) : {reply_robot_lang}"
            )

        chosen_voice = self._tts_voice_for_robot_locale(robot_lang_setting, voice_name)
        safe_console_line(
            f"Synthese vocale finale (langue du robot / voix Azure) voix={chosen_voice}"
        )

        output_audio = self.text_to_speech(reply_robot_lang, chosen_voice)
        safe_console_line(
            f"Audio genere : {len(output_audio)} octets (flux WAV)."
        )
        safe_console_line("========== Fin pipeline ==========")

        return {
            "robot_lang": robot_lang_setting,
            "input_text": input_text,
            "extra_text": (str(extra_text).strip() if extra_text and str(extra_text).strip() else None),
            "question_combined": question_for_n8n,
            "text_fr_for_n8n": text_fr_for_n8n,
            "reply_fr": reply_fr,
            "reply_text": reply_robot_lang,
            "audio_bytes": output_audio,
        }

    # =========================================================
    # --- YOUTUBE/MUSIC CACHE (yt-dlp on the backend) ---
    # =========================================================
    # The Pi often runs on a network that blocks outbound Internet (e.g. ISET school
    # WiFi) but can reach the backend on the LAN. We therefore do the YouTube
    # download here and serve the cached WAV via the StaticFiles mount in main.py.
    _MUSIC_CACHE_DIR = Path("cache/music")
    _YT_PLAYER_CLIENTS = ("android", "ios", "tv", "web")

    @classmethod
    def _music_cache_path_for(cls, url: str) -> Path:
        cls._MUSIC_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
        return cls._MUSIC_CACHE_DIR / f"{digest}.wav"

    def _download_youtube_to_cache(self, url: str, *, timeout_seconds: float = 90.0) -> Path:
        """Ensure a YouTube URL is downloaded to the local music cache. Returns the cached WAV path.

        Tries multiple yt-dlp player_client values to bypass YouTube's bot check.
        Raises RuntimeError if every attempt fails.
        """
        if not url or not str(url).strip():
            raise ValueError("_download_youtube_to_cache called with empty url")
        url = str(url).strip()

        cache_path = self._music_cache_path_for(url)
        if cache_path.exists() and cache_path.stat().st_size > 0:
            safe_console_line(f"[music] cache hit: {cache_path.name}")
            return cache_path

        if not shutil.which("yt-dlp"):
            raise RuntimeError(
                "yt-dlp not installed on the backend. Install with: pip install yt-dlp"
            )

        out_template = str(cache_path.with_suffix("")) + ".%(ext)s"
        last_error = ""
        for attempt, client in enumerate(self._YT_PLAYER_CLIENTS, start=1):
            cmd = [
                "yt-dlp",
                "--quiet",
                "--no-warnings",
                "--no-playlist",
                "--extract-audio",
                "--audio-format", "wav",
                "--audio-quality", "0",
                "--extractor-args", f"youtube:player_client={client}",
                "-o", out_template,
                url,
            ]
            safe_console_line(
                f"[music] yt-dlp attempt {attempt}/{len(self._YT_PLAYER_CLIENTS)} "
                f"(player_client={client}) for {url}"
            )
            try:
                completed = subprocess.run(
                    cmd,
                    timeout=timeout_seconds,
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
            except subprocess.TimeoutExpired:
                last_error = f"timeout after {timeout_seconds:.0f}s (client={client})"
                safe_console_line(f"[music] {last_error}")
                continue
            if completed.returncode == 0 and cache_path.exists() and cache_path.stat().st_size > 0:
                safe_console_line(f"[music] cached: {cache_path.name} ({cache_path.stat().st_size} bytes)")
                return cache_path
            last_error = (completed.stderr or b"").decode("utf-8", errors="replace").strip()
            safe_console_line(
                f"[music] client={client} failed (code {completed.returncode}): {last_error[:200]}"
            )
            if cache_path.exists():
                try:
                    cache_path.unlink()
                except OSError:
                    pass
        raise RuntimeError(
            f"yt-dlp failed for all player clients ({', '.join(self._YT_PLAYER_CLIENTS)}). "
            f"Last error: {last_error[:400]}"
        )

    @staticmethod
    def _music_lan_url(cache_path: Path) -> str:
        """Convert a local cache path into the URL the Pi will fetch over the LAN.
        Uses a path-only URL so the FastAPI request's host header determines the origin
        (works for SALAH_DESKTOP.local, raw IP, or anything else the Pi reaches us via).
        """
        return f"/cache/music/{cache_path.name}"

    # =========================================================
    # --- ACTION DISPATCHER (multi-type n8n responses) ---
    # =========================================================
    # Direction words used by the n8n "Test" code node. Keep this in sync
    # with the workflow's `directions` array — otherwise the dispatcher will
    # silently fall back to "text" for movements.
    _DIRECTION_WORD_TO_COMMAND = {
        "avant": "forward",
        "derriere": "backward",
        "derrière": "backward",
        "gauche": "left",
        "droite": "right",
        "stop": "stop",
        "stope": "stop",
    }

    # =========================================================
    # --- EMOTION / EXPRESSION DU VISAGE ---
    # =========================================================
    # Les agents n8n terminent CHAQUE réponse par une émotion entre
    # parenthèses, ex. « ... après la cérémonie ? (content) ». On doit :
    #   1. retirer cette grimace AVANT le TTS (sinon le robot prononce le mot),
    #   2. la traduire en une catégorie de visage que la Pi sait afficher.
    #
    # Le vocabulaire varie selon l'agent qui répond :
    #   - agent conversation simple : surpris / heureux / curieux / amoureux /
    #     en colère / triste,
    #   - agent mémoire profonde : + content, fier, pensif, amusé, inquiet,
    #     touché, sceptique, soulagé, admiratif, taquin, nostalgique,
    #   - agent greet : champ JSON séparé `emotion_visuelle`
    #     (heureux | triste | en_colere | surpris | amoureux).
    # On couvre tout ce vocabulaire (accents ignorés) ; les 5 catégories
    # correspondent aux visages 3/4/5/6/8 de la Pi, `neutral` = repli (0).
    _EMOTION_TO_EXPRESSION = {
        # --- positif / joyeux → HAPPY (3) ---
        "heureux": "happy", "heureuse": "happy",
        "content": "happy", "contente": "happy",
        "curieux": "happy", "curieuse": "happy",
        "joyeux": "happy", "joyeuse": "happy", "ravi": "happy", "ravie": "happy",
        "fier": "happy", "fiere": "happy",
        "amuse": "happy", "amusant": "happy", "taquin": "happy",
        "soulage": "happy", "enthousiaste": "happy",
        # --- étonnement / admiration → SURPRISED (8) ---
        "surpris": "surprised", "surprise": "surprised", "surprix": "surprised",
        "etonne": "surprised", "etonnee": "surprised",
        "admiratif": "surprised", "impressionne": "surprised",
        # --- affection / ému → LOVE (4) ---
        "amoureux": "love", "amoureuse": "love",
        "touche": "love", "touchee": "love", "attendri": "love", "tendre": "love",
        # --- colère / agacement → ANGRY (5) ---
        "en colere": "angry", "colere": "angry",
        "fache": "angry", "enerve": "angry", "agace": "angry", "contrarie": "angry",
        # --- tristesse / inquiétude → SAD (6) ---
        "triste": "sad", "inquiet": "sad", "inquiete": "sad",
        "decu": "sad", "peine": "sad", "melancolique": "sad", "nostalgique": "sad",
        # --- pensif / neutre → NEUTRAL (0) ---
        "pensif": "neutral", "pensive": "neutral",
        "sceptique": "neutral", "perplexe": "neutral", "calme": "neutral",
        "neutre": "neutral",
    }

    @staticmethod
    def _strip_accents(text: str) -> str:
        import unicodedata
        return "".join(
            ch for ch in unicodedata.normalize("NFD", text)
            if unicodedata.category(ch) != "Mn"
        )

    @classmethod
    def _emotion_to_expression(cls, word: Optional[str]) -> Optional[str]:
        """Mappe un mot d'émotion FR (accents/casse/underscore tolérés) vers une
        catégorie de visage Pi, ou None si inconnu."""
        if not word:
            return None
        key = cls._strip_accents(str(word)).lower().strip()
        key = key.replace("_", " ").strip()
        if key in cls._EMOTION_TO_EXPRESSION:
            return cls._EMOTION_TO_EXPRESSION[key]
        # « en colère » / « en colere » : on retombe sur le dernier mot.
        if " " in key:
            last = key.rsplit(" ", 1)[-1]
            return cls._EMOTION_TO_EXPRESSION.get(last)
        return None

    @classmethod
    def _split_emotion_suffix(cls, text: str):
        """Sépare le texte FR de la grimace finale entre parenthèses.

        Retourne ``(texte_nettoye, expression)`` où ``expression`` est une des
        catégories de ``_EMOTION_TO_EXPRESSION`` (ou ``"neutral"`` par défaut).

        On ne retire QUE si le contenu des parenthèses finales correspond à une
        émotion connue — ainsi un titre de chanson « Song (Live) » ou toute
        autre parenthèse légitime reste intact.
        """
        import re
        if not text:
            return text, "neutral"
        stripped = text.rstrip()
        match = re.search(r"\(\s*([^()]{2,40}?)\s*\)\s*$", stripped)
        if not match:
            return text, "neutral"
        expression = cls._emotion_to_expression(match.group(1))
        if expression is None:
            # Parenthèse finale non reconnue comme émotion → on n'y touche pas.
            return text, "neutral"
        clean = stripped[: match.start()].rstrip()
        return clean, expression

    @classmethod
    def _find_emotion_visuelle(cls, payload):
        """Cherche un champ `emotion_visuelle` (agent greet) dans une réponse
        n8n éventuellement imbriquée ou encodée en chaîne JSON. None si absent."""
        import json as _json
        if isinstance(payload, str):
            s = payload.strip()
            if s.startswith("```"):
                import re as _re
                s = _re.sub(r"^```[a-zA-Z]*\s*", "", s)
                s = _re.sub(r"\s*```$", "", s).strip()
            if s.startswith("{") or s.startswith("["):
                try:
                    return cls._find_emotion_visuelle(_json.loads(s))
                except (ValueError, TypeError):
                    return None
            return None
        if isinstance(payload, dict):
            for key in ("emotion_visuelle", "emotion", "vibe_initiale"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
            for value in payload.values():
                found = cls._find_emotion_visuelle(value)
                if found:
                    return found
        if isinstance(payload, list):
            for item in payload:
                found = cls._find_emotion_visuelle(item)
                if found:
                    return found
        return None

    def _interpret_n8n_envelope(self, envelope: dict) -> dict:
        """
        Map the raw n8n response (from N8NClient.trigger_workflow_raw) to a structured
        action. Returns a dict with at least:
          {
            "action": "text" | "music" | "motion" | "sleep" | "error",
            "spoken_text": str,        # what to TTS for the user (announce / acknowledge / reply)
            "music_url": str | None,   # YouTube URL when action=music
            "music_title": str | None,
            "motion_command": str | None,  # forward/backward/left/right/stop
            "raw_text": str,           # original textual content for debugging
          }
        """
        result = {
            "action": "text",
            "spoken_text": "",
            "music_url": None,
            "music_title": None,
            "motion_command": None,
            "raw_text": "",
        }
        if not envelope or not envelope.get("ok"):
            result["action"] = "error"
            result["spoken_text"] = envelope.get("error") if envelope else "n8n unreachable"
            return result

        json_body = envelope.get("json")
        text_body = (envelope.get("text") or "").strip()
        result["raw_text"] = text_body

        # ----- 1) Music branch: JSON with lienChanson + nomChanson ------------------
        if isinstance(json_body, dict) and json_body.get("lienChanson"):
            title = (json_body.get("nomChanson") or "").strip()
            result["action"] = "music"
            result["music_url"] = str(json_body.get("lienChanson")).strip()
            result["music_title"] = title or None
            # Announcement TTS — backend says it in robot's locale upstream.
            result["spoken_text"] = (
                f"Je vais te jouer {title}" if title else "Je joue ta musique tout de suite"
            )
            return result

        # n8n also wraps JSON arrays sometimes ([{...}]) — handle that.
        if isinstance(json_body, list) and json_body:
            first = json_body[0]
            if isinstance(first, dict) and first.get("lienChanson"):
                title = (first.get("nomChanson") or "").strip()
                result["action"] = "music"
                result["music_url"] = str(first.get("lienChanson")).strip()
                result["music_title"] = title or None
                result["spoken_text"] = (
                    f"Je vais te jouer {title}" if title else "Je joue ta musique tout de suite"
                )
                return result

        # ----- 2) Sleep / shutdown branch: plain text "I am Closed " ---------------
        if "i am closed" in text_body.lower():
            result["action"] = "sleep"
            result["spoken_text"] = "Bonne nuit, à bientôt"
            return result

        # ----- 3) Sleep-mode reply (etat=0): "Je suis Fermeé pour le moment…" -----
        if "ferme" in text_body.lower() and "moment" in text_body.lower():
            result["action"] = "sleep"
            result["spoken_text"] = text_body  # the robot reads its own canned message
            return result

        # ----- 4) Wake / unlock branch: plain text "Yo Yo" -------------------------
        if text_body.strip().lower() in {"yo yo", "yo"}:
            result["action"] = "text"
            result["spoken_text"] = "Me revoilà ! Je t'écoute"
            return result

        # ----- 5) Direction branch: "direction\n<message>" -------------------------
        # The workflow's `Respond Direction` node emits: f"{intention}\n{messageOriginal}".
        lines = [ln.strip() for ln in text_body.splitlines() if ln.strip()]
        if lines and lines[0].lower() == "direction":
            haystack = " ".join(lines[1:]).lower() if len(lines) > 1 else ""
            for word, command in self._DIRECTION_WORD_TO_COMMAND.items():
                if word in haystack:
                    result["action"] = "motion"
                    result["motion_command"] = command
                    result["spoken_text"] = self._motion_announcement(command)
                    return result
            # Direction word missing from payload — degrade to plain text.

        # ----- 6) Text branch: JSON `{ "output": "..." }` or just a string ---------
        text_reply = self._extract_text_from_n8n_response(json_body if json_body is not None else text_body)
        result["action"] = "text"
        result["spoken_text"] = text_reply or text_body or ""
        return result

    # Motion announcements are spoken on EVERY motion turn. TTS round-trip to
    # Azure is 1-3 s — for 5 fixed strings, we cache the audio at first use
    # and skip the synth call entirely on subsequent turns. Per-locale cache
    # keyed by (locale, command).
    _MOTION_TTS_CACHE: dict = {}

    @staticmethod
    def _motion_announcement(command: str) -> str:
        return {
            "forward": "OK, j'avance",
            "backward": "OK, je recule",
            "left": "OK, je tourne à gauche",
            "right": "OK, je tourne à droite",
            "stop": "Je m'arrête",
        }.get(command, "OK")

    def _cached_motion_tts(
        self,
        command: str,
        spoken_text: str,
        robot_lang_setting: str,
        voice_name: Optional[str],
    ) -> bytes:
        """Return TTS audio for a motion announcement, synthesising once per (lang, command)."""
        if not spoken_text:
            return b""
        cache_key = (robot_lang_setting, command, spoken_text, voice_name or "")
        cached = self._MOTION_TTS_CACHE.get(cache_key)
        if cached is not None:
            safe_console_line(f"[motion-tts] cache hit for {command!r} ({robot_lang_setting})")
            return cached
        chosen_voice = self._tts_voice_for_robot_locale(robot_lang_setting, voice_name)
        audio = self.text_to_speech(spoken_text, chosen_voice)
        self._MOTION_TTS_CACHE[cache_key] = audio
        safe_console_line(f"[motion-tts] cached {command!r} for {robot_lang_setting} ({len(audio)} bytes)")
        return audio

    def audio_to_n8n_to_action(self, audio_bytes: bytes, voice_name=None, extra_text=None, image_bytes=None):
        """
        Like audio_to_n8n_to_audio but supports multi-type responses.

        ``image_bytes`` (optionnel) : photo de la personne. Quand elle est
        fournie (cas personne inconnue côté Pi), on poste à n8n en
        multipart/form-data avec un champ binaire ``image`` — pour que le
        workflow puisse enregistrer un nouveau visage si la question est une
        présentation. Sans image, on garde le POST JSON ``{"message": …}``.

        Returns:
            {
              "action": "text" | "music" | "motion" | "sleep" | "error",
              "robot_lang": str,
              "input_text": str,
              "spoken_text": str,         # localized for the robot, already TTS'd
              "audio_bytes": bytes,       # WAV bytes for `spoken_text`
              "music_url": str | None,
              "music_title": str | None,
              "motion_command": str | None,
            }
        """
        import time as _time
        t_pipeline_start = _time.perf_counter()

        def _step_log(label: str, t_step_start: float) -> None:
            ms = int((_time.perf_counter() - t_step_start) * 1000)
            total_ms = int((_time.perf_counter() - t_pipeline_start) * 1000)
            safe_console_line(f"⏱️  [{ms:5d} ms]  {label:<22}  (total {total_ms} ms)")

        safe_console_line("========== Pipeline audio -> n8n -> action ==========")
        t_step = _time.perf_counter()
        langue_brute = self._get_robot_langue_from_setting()
        robot_lang_setting = self._canonical_locale_for_speech_and_translation(langue_brute)
        robot_tr = self._bcp47_primary(robot_lang_setting)
        _step_log("setting.langue lookup", t_step)

        t_step = _time.perf_counter()
        stt_result = self.speech_to_text(audio_bytes)
        _step_log("STT (Azure recognize)", t_step)

        input_text = (stt_result or {}).get("text", "").strip()
        question_for_n8n = self._compose_stt_with_extra_text(input_text, extra_text)
        if not question_for_n8n:
            raise RuntimeError("Aucun texte reconnu depuis l'audio.")
        if not input_text and extra_text and str(extra_text).strip():
            safe_console_line(
                f"STT vide — envoi n8n avec identite seule : {question_for_n8n!r}"
            )

        t_step = _time.perf_counter()
        if robot_tr == "fr":
            text_fr_for_n8n = question_for_n8n
        else:
            text_fr_for_n8n = self.translator.translate_text(
                question_for_n8n, robot_lang_setting, "fr-FR"
            )
        _step_log(f"translate→fr (tr={robot_tr})", t_step)

        t_step = _time.perf_counter()
        if image_bytes:
            safe_console_line(
                f"Image jointe ({len(image_bytes)} octets) — POST multipart vers n8n "
                f"(champ binaire « image », cas inconnu/présentation)."
            )
            envelope = self.n8n.trigger_workflow_raw_multipart(text_fr_for_n8n, image_bytes)
        else:
            envelope = self.n8n.trigger_workflow_raw({"message": text_fr_for_n8n})
        _step_log("n8n webhook roundtrip", t_step)

        action = self._interpret_n8n_envelope(envelope)
        safe_console_line(f"Action interprétée : {action['action']} | command={action['motion_command']} | url={action['music_url']}")

        # For music actions, do the YouTube download here (the Pi often has no public
        # Internet but can always reach our LAN cache). On failure we degrade to a
        # spoken apology rather than crashing the whole turn.
        if action["action"] == "music" and action.get("music_url"):
            t_step = _time.perf_counter()
            try:
                cache_path = self._download_youtube_to_cache(action["music_url"])
                action["music_url"] = self._music_lan_url(cache_path)
                safe_console_line(f"Music cached → served at {action['music_url']}")
            except Exception as exc:
                safe_console_line(f"Music download failed: {exc!s}")
                action["action"] = "text"
                action["music_url"] = None
                action["music_title"] = None
                action["spoken_text"] = (
                    "Je n'arrive pas à télécharger cette musique, désolé"
                )
            _step_log("yt-dlp download", t_step)

        # Translate spoken_text to robot language if needed (announcements are French).
        t_step = _time.perf_counter()
        spoken_fr = action.get("spoken_text") or ""
        # Retirer la grimace « (émotion) » que les agents ajoutent en fin de
        # réponse AVANT toute traduction/TTS — sinon le robot la prononce.
        spoken_fr, expression = self._split_emotion_suffix(spoken_fr)
        if expression != "neutral":
            safe_console_line(f"Émotion détectée : {expression!r} (visage)")
        if not spoken_fr:
            spoken_robot = ""
        elif robot_tr == "fr":
            spoken_robot = spoken_fr
        else:
            try:
                spoken_robot = self.translator.translate_text(spoken_fr, "fr-FR", robot_lang_setting)
            except Exception:
                # Translation hiccups should not block the action — fall back to French.
                spoken_robot = spoken_fr
        _step_log(f"translate→{robot_tr}", t_step)

        t_step = _time.perf_counter()
        if action["action"] == "motion" and action.get("motion_command"):
            # Hit the per-(locale, command) cache — saves ~1-3s on every
            # forward/backward/left/right/stop after the first use.
            audio_out = self._cached_motion_tts(
                action["motion_command"], spoken_robot, robot_lang_setting, voice_name,
            )
            _step_log("TTS (motion cached)", t_step)
        elif spoken_robot:
            chosen_voice = self._tts_voice_for_robot_locale(robot_lang_setting, voice_name)
            audio_out = self.text_to_speech(spoken_robot, chosen_voice)
            _step_log("TTS (Azure synthesize)", t_step)
        else:
            audio_out = b""
            _step_log("TTS skipped (empty text)", t_step)

        safe_console_line(
            f"========== Pipeline complete: action={action['action']} "
            f"total={int((_time.perf_counter() - t_pipeline_start) * 1000)} ms =========="
        )
        return {
            "action": action["action"],
            "robot_lang": robot_lang_setting,
            "input_text": input_text,
            "spoken_text": spoken_robot,
            "audio_bytes": audio_out,
            "music_url": action["music_url"],
            "music_title": action["music_title"],
            "motion_command": action["motion_command"],
            "expression": expression,
        }

    # =========================================================
    # --- PASSIVE GREET PIPELINE (5-minute idle wake) ---
    # =========================================================
    def name_to_action(self, nom: str, voice_name=None):
        """Pipeline démarrage de conversation : nom -> n8n greet -> TTS.

        Déclenché par la Pi après 5 minutes d'inactivité. Pas de STT
        (la Pi a déjà identifié le visage). Pipeline :
            nom (str)
              -> traduction vers français (si la langue robot != fr)
              -> webhook n8n greet (workflow "démarrer la conversation")
              -> traduction du résultat vers la langue du robot
              -> Azure TTS
              -> renvoie le même shape que audio_to_n8n_to_action.

        Returns:
            {
              "action": "text",
              "robot_lang": str,
              "input_text": str,           # le nom envoyé
              "spoken_text": str,          # texte parlé (langue du robot)
              "audio_bytes": bytes,        # WAV TTS du spoken_text
              "music_url": None,
              "music_title": None,
              "motion_command": None,
            }
        """
        import time as _time
        t_pipeline_start = _time.perf_counter()

        def _step_log(label: str, t_step_start: float) -> None:
            ms = int((_time.perf_counter() - t_step_start) * 1000)
            total_ms = int((_time.perf_counter() - t_pipeline_start) * 1000)
            safe_console_line(f"⏱️  [{ms:5d} ms]  {label:<24}  (total {total_ms} ms)")

        safe_console_line("========== Pipeline greet (nom -> n8n -> action) ==========")
        clean_name = (nom or "").strip() or "inconnu"
        # Visage non reconnu : le workflow n8n attend le sentinelle EXACT "unkonu"
        # (branche "premier contact" / AI Agent3). On mappe notre fallback dessus.
        if clean_name.lower() in ("inconnu", "inconnue", "unknown"):
            clean_name = "unkonu"

        t_step = _time.perf_counter()
        langue_brute = self._get_robot_langue_from_setting()
        robot_lang_setting = self._canonical_locale_for_speech_and_translation(langue_brute)
        robot_tr = self._bcp47_primary(robot_lang_setting)
        _step_log("setting.langue lookup", t_step)

        # Payload envoyé à n8n : on garde la clé `nom` que le workflow attend,
        # plus une clé `message` "Bonjour, voici la personne devant moi : <nom>"
        # pour les workflows qui s'attendent au format conversationnel standard.
        n8n_payload = {"nom": clean_name, "message": clean_name}

        t_step = _time.perf_counter()
        envelope = self.n8n.trigger_greet_workflow(n8n_payload)
        _step_log("n8n greet roundtrip", t_step)

        if not envelope.get("ok"):
            err = envelope.get("error") or "n8n greet failed"
            safe_console_line(f"Erreur n8n greet : {err}")
            raise RuntimeError(err)

        reply_fr = self._extract_text_from_n8n_response(
            envelope.get("json") if envelope.get("json") is not None else envelope.get("text")
        )
        if not reply_fr:
            raise RuntimeError("Le workflow greet n'a pas renvoyé de texte exploitable.")
        safe_console_line(f"Réponse n8n greet (FR) : {reply_fr!r}")

        # Émotion → visage. L'agent greet renvoie un champ JSON dédié
        # `emotion_visuelle` ; les autres agents collent la grimace « (émotion) »
        # en fin de texte. On gère les deux, le champ dédié primant.
        expression = self._emotion_to_expression(
            self._find_emotion_visuelle(envelope.get("json"))
        ) or "neutral"
        reply_fr, suffix_expression = self._split_emotion_suffix(reply_fr)
        if expression == "neutral":
            expression = suffix_expression
        if expression != "neutral":
            safe_console_line(f"Émotion greet détectée : {expression!r} (visage)")

        # Traduction vers la langue du robot (le workflow renvoie du FR).
        t_step = _time.perf_counter()
        if robot_tr == "fr":
            spoken_robot = reply_fr
        else:
            try:
                spoken_robot = self.translator.translate_text(reply_fr, "fr-FR", robot_lang_setting)
            except Exception:
                # Translation hiccups ne doivent pas bloquer le greet — on
                # retombe sur le français.
                safe_console_line("Traduction echouee — fallback FR")
                spoken_robot = reply_fr
        _step_log(f"translate→{robot_tr}", t_step)

        # TTS
        t_step = _time.perf_counter()
        chosen_voice = self._tts_voice_for_robot_locale(robot_lang_setting, voice_name)
        audio_out = self.text_to_speech(spoken_robot, chosen_voice)
        _step_log("TTS (Azure synthesize)", t_step)

        safe_console_line(
            f"========== Greet complete: nom={clean_name!r} "
            f"total={int((_time.perf_counter() - t_pipeline_start) * 1000)} ms =========="
        )
        return {
            "action": "text",
            "robot_lang": robot_lang_setting,
            "input_text": clean_name,
            "spoken_text": spoken_robot,
            "audio_bytes": audio_out,
            "music_url": None,
            "music_title": None,
            "motion_command": None,
            "expression": expression,
        }

    # =========================================================
    # --- GEMINI KEYWORDS ---
    # =========================================================
    def generate_robot_name_keywords(self):
        robot_name = self._get_robot_name_from_setting()
        if not robot_name:
            raise RuntimeError("Le champ 'name' de la table setting est vide ou introuvable.")

        raw_output = self.gemini.generate_keywords_from_name(robot_name)

        try:
            parsed = json.loads(raw_output)
            if not isinstance(parsed, list):
                raise RuntimeError("La réponse Gemini n'est pas une liste JSON.")
            return {
                "name": robot_name,
                "keywords": parsed
            }
        except json.JSONDecodeError:
            # Fallback si Gemini encapsule le JSON dans des balises markdown.
            cleaned = raw_output.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(cleaned)
            if not isinstance(parsed, list):
                raise RuntimeError("La réponse Gemini n'est pas une liste JSON.")
            return {
                "name": robot_name,
                "keywords": parsed
            }

    def _validate_azure_speech_config(self):
        if not settings.AZURE_SPEECH_KEY or not settings.AZURE_SPEECH_REGION:
            raise RuntimeError(
                "Configuration Azure Speech manquante. Définissez AZURE_SPEECH_KEY et AZURE_SPEECH_REGION dans le fichier .env."
            )

    def _extract_text_from_n8n_response(self, payload):
        import json as _json
        import re as _re

        if isinstance(payload, str):
            s = payload.strip()
            # The AI Agent nodes often wrap their JSON in a markdown code fence:
            # ```json\n{...}\n```  (or ```\n{...}\n```). Strip it before parsing.
            if s.startswith("```"):
                s = _re.sub(r"^```[a-zA-Z]*\s*", "", s)
                s = _re.sub(r"\s*```$", "", s).strip()
            # The greet/first-contact agents return their text as a JSON *string*,
            # e.g. '{"parole_du_robot": "...", "emotion_visuelle": "..."}' or
            # '{"output": "..."}'. Parse it and dig out the spoken text.
            if s.startswith("{") or s.startswith("["):
                try:
                    nested = self._extract_text_from_n8n_response(_json.loads(s))
                    if nested:
                        return nested
                except (ValueError, TypeError):
                    pass
            return s

        if isinstance(payload, dict):
            # Spoken-text keys across the KODA workflows: main dialogue ("reponce"
            # — typo kept), greet AI Agent ("parole_du_robot"), first-contact agent
            # ("premiere_parole"). "reponce"/"réponse" first so the main path wins.
            direct_keys = [
                "parole_du_robot", "premiere_parole",
                "reponce", "réponse", "reply",
                "text", "response", "answer", "message", "output", "result",
            ]
            for key in direct_keys:
                value = payload.get(key)
                if value is None:
                    continue
                # The value may itself be a JSON string (agent output) or a nested
                # object/list — recurse so we land on the actual spoken text.
                extracted = self._extract_text_from_n8n_response(value)
                if extracted:
                    return extracted

            # Certains workflows retournent un objet imbriqué.
            for value in payload.values():
                extracted = self._extract_text_from_n8n_response(value)
                if extracted:
                    return extracted

        if isinstance(payload, list):
            for item in payload:
                extracted = self._extract_text_from_n8n_response(item)
                if extracted:
                    return extracted

        return None

    def _get_robot_name_from_setting(self):
        return self._setting_cached("name")

    def _get_known_faces(self):
        now = time.time()
        if self._known_faces_cache and (now - self._known_faces_cache_at) < self._known_faces_ttl_seconds:
            return self._known_faces_cache

        # Stale-while-revalidate: ne bloque pas la requête si on a déjà un cache.
        if self._known_faces_cache:
            if not self._is_refreshing_faces:
                threading.Thread(target=self._refresh_known_faces_cache, daemon=True).start()
            return self._known_faces_cache

        # Premier chargement: on calcule immédiatement pour avoir un référentiel.
        self._refresh_known_faces_cache()
        return self._known_faces_cache

    def _invalidate_known_faces_cache(self):
        with self._cache_lock:
            self._known_faces_cache = []
            self._known_faces_cache_at = 0.0

    def _refresh_known_faces_cache(self):
        with self._cache_lock:
            if self._is_refreshing_faces:
                return
            self._is_refreshing_faces = True
        try:
            now = time.time()
            if not FACE_RECOGNITION_AVAILABLE:
                self._known_faces_cache = []
                self._known_faces_cache_at = now
                return
            try:
                rows = self.client.table("imageuser").select("idimage, iduser, url").execute().data or []
            except Exception:
                rows = []
            if not rows:
                self._known_faces_cache = []
                self._known_faces_cache_at = now
                return

            users_rows = self.client.table("utilisateur").select("iduser, nom").execute().data or []
            nom_by_user = {}
            for u in users_rows:
                uid = u.get("iduser")
                if uid is None:
                    continue
                try:
                    nom_by_user[int(uid)] = str(u.get("nom") or "inconnu")
                except (TypeError, ValueError):
                    nom_by_user[str(uid)] = str(u.get("nom") or "inconnu")

            known_faces = []
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = []
                for row in rows:
                    url = (row.get("url") or "").strip()
                    if not url:
                        continue
                    uid = row.get("iduser")
                    try:
                        uid_int = int(uid) if uid is not None else None
                    except (TypeError, ValueError):
                        uid_int = None
                    nom = "inconnu"
                    if uid_int is not None and uid_int in nom_by_user:
                        nom = nom_by_user[uid_int]
                    elif uid is not None and str(uid) in nom_by_user:
                        nom = nom_by_user[str(uid)]
                    futures.append(executor.submit(self._extract_encoding_from_url, url, nom))
                for future in as_completed(futures):
                    result = future.result()
                    if result is not None:
                        known_faces.append(result)

            self._known_faces_cache = known_faces
            self._known_faces_cache_at = now
        finally:
            with self._cache_lock:
                self._is_refreshing_faces = False

    def _extract_encoding_from_url(self, image_url: str, nom: str):
        if not image_url:
            return None
        try:
            response = httpx.get(image_url, timeout=10)
            if response.status_code != 200:
                return None
            user_image = face_recognition.load_image_file(io.BytesIO(response.content))
            user_image = self._resize_image_for_speed(user_image, max_width=800)
            user_locations = face_recognition.face_locations(user_image, model="hog")
            user_encodings = face_recognition.face_encodings(
                user_image,
                known_face_locations=user_locations,
                num_jitters=1
            )
            if not user_encodings:
                return None
            return {
                "nom": nom or "inconnu",
                "encoding": user_encodings[0]
            }
        except Exception:
            return None

    def _resize_image_for_speed(self, image, max_width=800):
        height, width = image.shape[:2]
        if width <= max_width:
            return image
        ratio = max_width / float(width)
        new_height = int(height * ratio)
        # Sous-échantillonnage rapide pour accélérer face_locations/encodings.
        step = max(1, int(width / max_width))
        resized = image[::step, ::step]
        if resized.shape[1] > max_width:
            resized = resized[:new_height, :max_width]
        return resized

    def _fix_booleans(self, data: dict) -> dict:
        new_data = data.copy()
        for k, v in new_data.items():
            if isinstance(v, bool):
                new_data[k] = 1 if v else 0
            elif isinstance(v, datetime):
                new_data[k] = v.isoformat()
        return new_data