import asyncio
import base64
import json
import logging
import time

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from src.application.app_service_impl import ApiServiceImpl
from src.application.nightly_scheduler import get_scheduler_status
from src.application.wake_word_stream import WakeWordStreamSession
from src.controllers.schemas import (
    AccompagnementCreate,
    AccompagnementUpdate,
    AgendaCreate,
    AgendaUpdate,
    ActivityCreate,
    ActivityUpdate,
    AuthentificationCreate,
    AuthentificationUpdate,
    ConversationCreate,
    ConversationUpdate,
    HistoriqueCreate,
    InformationPersonelleCreate,
    InformationPersonelleUpdate,
    ImageUserCreate,
    ImageUserUpdate,
    LoginRequest,
    NomGreetRequest,
    NoteCreate,
    NoteUpdate,
    SettingUpdate,
    TextToSpeechRequest,
    UtilisateurCreate,
    UtilisateurUpdate,
)

router = APIRouter()
service = ApiServiceImpl()

# ==============================================================
# ENDPOINTS UTILISATEURS
# ==============================================================
@router.get("/users", summary="Lister tous les utilisateurs")
def get_users():
    return service.get_all_users()


@router.get("/users/{iduser}", summary="Obtenir un utilisateur par iduser")
def get_user(iduser: int):
    row = service.get_user(iduser)
    if not row:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return row


@router.post("/users", summary="Créer un utilisateur", status_code=201)
def create_user(data: UtilisateurCreate):
    return service.create_user(data.model_dump(exclude_none=True))


@router.put("/users/{iduser}", summary="Mettre à jour un utilisateur")
def update_user(iduser: int, data: UtilisateurUpdate):
    payload = data.model_dump(exclude_none=True)
    if not payload:
        raise HTTPException(status_code=400, detail="Aucun champ à mettre à jour")
    return service.update_user(iduser, payload)


@router.delete("/users/{iduser}", summary="Supprimer un utilisateur")
def delete_user(iduser: int):
    return service.delete_user(iduser)

# ==============================================================
# ENDPOINTS IMAGES UTILISATEUR (table imageuser)
# ==============================================================
@router.get("/user-images", summary="Lister les images utilisateur")
def list_user_images():
    return service.get_all_user_images()


@router.get("/user-images/{idimage}", summary="Obtenir une ligne imageuser")
def get_user_image_row(idimage: int):
    row = service.get_user_image(idimage)
    if not row:
        raise HTTPException(status_code=404, detail="Image utilisateur introuvable")
    return row


@router.get("/user-images/by-user/{iduser}", summary="Images pour un iduser")
def get_user_images_for_user(iduser: int):
    return service.get_user_images_by_user(iduser)


@router.post("/user-images", summary="Enregistrer une image utilisateur (url)", status_code=201)
def create_user_image(data: ImageUserCreate):
    return service.create_user_image(data.model_dump(exclude_none=True))


@router.put("/user-images/{idimage}", summary="Mettre à jour une image utilisateur")
def update_user_image_row(idimage: int, data: ImageUserUpdate):
    payload = data.model_dump(exclude_none=True)
    if not payload:
        raise HTTPException(status_code=400, detail="Aucun champ à mettre à jour")
    return service.update_user_image(idimage, payload)


@router.delete("/user-images/{idimage}", summary="Supprimer une image utilisateur")
def delete_user_image_row(idimage: int):
    return service.delete_user_image(idimage)

# ==============================================================
# ENDPOINTS HISTORIQUE
# ==============================================================
@router.get("/history", summary="Lister tout l'historique")
def get_history():
    return service.get_all_history()


@router.get("/history/{historique_id}", summary="Obtenir une entrée d'historique")
def get_historique(historique_id: int):
    row = service.get_historique(historique_id)
    if not row:
        raise HTTPException(status_code=404, detail="Historique introuvable")
    return row


@router.post("/history", summary="Ajouter une entrée d'historique", status_code=201)
def create_historique(data: HistoriqueCreate):
    return service.create_historique(data.model_dump(exclude_none=True))


@router.delete("/history/{historique_id}", summary="Supprimer une entrée d'historique")
def delete_historique(historique_id: int):
    return service.delete_historique(historique_id)

# ==============================================================
# ENDPOINTS CONVERSATIONS
# ==============================================================
@router.get("/conversations/last100", summary="100 dernières conversations")
def get_convs():
    return service.get_last_100_conversations()


@router.get("/conversations", summary="Lister toutes les conversations")
def list_conversations():
    return service.get_all_conversations()


@router.get("/conversations/{conversation_id}", summary="Obtenir une conversation")
def get_conversation(conversation_id: int):
    row = service.get_conversation(conversation_id)
    if not row:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    return row


@router.post("/conversations", summary="Créer une conversation", status_code=201)
def create_conversation(data: ConversationCreate):
    return service.create_conversation(data.model_dump(exclude_none=True))


@router.put("/conversations/{conversation_id}", summary="Mettre à jour une conversation")
def update_conversation(conversation_id: int, data: ConversationUpdate):
    payload = data.model_dump(exclude_none=True)
    if not payload:
        raise HTTPException(status_code=400, detail="Aucune donnée fournie")
    return service.update_conversation(conversation_id, payload)


@router.delete("/conversations/{conversation_id}", summary="Supprimer une conversation")
def delete_conversation(conversation_id: int):
    return service.delete_conversation(conversation_id)

# ==============================================================
# ENDPOINTS NOTES
# ==============================================================
@router.get("/notes", summary="Lister toutes les notes")
def get_notes():
    return service.get_all_notes()


@router.get("/notes/{note_id}", summary="Obtenir une note")
def get_note(note_id: int):
    row = service.get_note(note_id)
    if not row:
        raise HTTPException(status_code=404, detail="Note introuvable")
    return row


@router.post("/notes", summary="Créer une note", status_code=201)
def create_note(data: NoteCreate):
    return service.create_note(data.model_dump(exclude_none=True))


@router.put("/notes/{note_id}", summary="Mettre à jour une note")
def update_note_full(note_id: int, data: NoteUpdate):
    payload = data.model_dump(exclude_none=True)
    if not payload:
        raise HTTPException(status_code=400, detail="Aucune donnée fournie")
    return service.update_note(note_id, payload)


@router.delete("/notes/{note_id}", summary="Supprimer une note")
def delete_note(note_id: int):
    return service.delete_note(note_id)


@router.patch("/notes/{note_id}/etat", summary="Modifier l'état d'une note")
def update_note_etat(note_id: int, etat: bool):
    return service.modify_note_etat(note_id, etat)

# ==============================================================
# ENDPOINTS SETTINGS
# ==============================================================
@router.get("/settings", summary="Obtenir les paramètres")
def get_settings():
    return service.get_settings()

@router.put("/settings", summary="Modifier les paramètres")
def update_settings(data: SettingUpdate):
    payload = data.model_dump(exclude_none=True)
    if not payload:
        raise HTTPException(status_code=400, detail="Aucun champ à mettre à jour")
    return service.modify_settings(payload)

# ==============================================================
# ENDPOINTS INFORMATIONS PERSONNELLES
# ==============================================================
@router.get("/personal-info", summary="Obtenir les informations personnelles")
def get_all_info():
    return service.get_personal_info()


@router.get("/personal-info/user/{iduser}", summary="Infos personnelles pour un utilisateur")
def get_personal_info_by_user(iduser: int):
    return service.get_personal_info_by_user(iduser)


@router.post("/personal-info", summary="Ajouter des informations personnelles", status_code=201)
def save_info(data: InformationPersonelleCreate):
    return service.add_personal_info(data.model_dump(exclude_none=True))


@router.put("/personal-info/{info_id}", summary="Mettre à jour une information personnelle")
def update_personal_info(info_id: int, data: InformationPersonelleUpdate):
    payload = data.model_dump(exclude_none=True)
    if not payload:
        raise HTTPException(status_code=400, detail="Aucune donnée fournie")
    return service.update_personal_info(info_id, payload)


@router.delete("/personal-info/{info_id}", summary="Supprimer une information personnelle")
def delete_personal_info(info_id: int):
    return service.delete_personal_info(info_id)


# ==============================================================
# ENDPOINTS ACCOMPAGNEMENT
# ==============================================================
@router.get("/accompagnements", summary="Lister tous les accompagnements")
def list_accompagnements():
    return service.get_all_accompagnements()


@router.get("/accompagnements/user/{iduser}", summary="Accompagnements par utilisateur")
def list_accompagnements_by_user(iduser: int):
    return service.get_accompagnements_by_user(iduser)


@router.get("/accompagnements/{accompagnement_id}", summary="Obtenir un accompagnement")
def get_accompagnement(accompagnement_id: int):
    row = service.get_accompagnement(accompagnement_id)
    if not row:
        raise HTTPException(status_code=404, detail="Accompagnement introuvable")
    return row


@router.post("/accompagnements", summary="Créer un accompagnement", status_code=201)
def create_accompagnement(data: AccompagnementCreate):
    return service.create_accompagnement(data.model_dump(exclude_none=True))


@router.put("/accompagnements/{accompagnement_id}", summary="Mettre à jour un accompagnement")
def update_accompagnement(accompagnement_id: int, data: AccompagnementUpdate):
    payload = data.model_dump(exclude_none=True)
    if not payload:
        raise HTTPException(status_code=400, detail="Aucune donnée fournie")
    return service.update_accompagnement(accompagnement_id, payload)


@router.delete("/accompagnements/{accompagnement_id}", summary="Supprimer un accompagnement")
def delete_accompagnement(accompagnement_id: int):
    return service.delete_accompagnement(accompagnement_id)


# ==============================================================
# ENDPOINTS AUTHENTIFICATION
# ==============================================================
@router.post("/auth/login", summary="Connexion client (email + mot de passe)")
def auth_login(data: LoginRequest):
    result = service.login(data.emailclient.strip(), data.motdepasse)
    if not result:
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    return {"status": "ok", "data": result}


@router.get("/auth/registrations", summary="Lister les enregistrements authentification")
def list_auth():
    return service.list_authentifications()


@router.get("/auth/registrations/{idproduit}", summary="Obtenir une ligne authentification par idproduit")
def get_auth(idproduit: int):
    row = service.get_authentification(idproduit)
    if not row:
        raise HTTPException(status_code=404, detail="Authentification introuvable")
    return row


@router.post("/auth/registrations", summary="Créer une authentification", status_code=201)
def create_auth(data: AuthentificationCreate):
    return service.create_authentification(data.model_dump(exclude_none=True))


@router.put("/auth/registrations/{idproduit}", summary="Mettre à jour une authentification")
def update_auth(idproduit: int, data: AuthentificationUpdate):
    payload = data.model_dump(exclude_none=True)
    if not payload:
        raise HTTPException(status_code=400, detail="Aucune donnée fournie")
    return service.update_authentification(idproduit, payload)


@router.delete("/auth/registrations/{idproduit}", summary="Supprimer une authentification")
def delete_auth(idproduit: int):
    return service.delete_authentification(idproduit)


# ==============================================================
# ENDPOINT N8N
# ==============================================================
@router.post("/trigger-n8n", summary="Déclencher un workflow n8n")
def trigger_n8n_workflow(payload: dict):
    """Envoie à n8n un JSON avec ``message`` (requis par le webhook). ``text`` est encore accepté et mappé vers ``message``."""
    return service.send_to_n8n(payload)

# ==============================================================
# ENDPOINTS AGENDA (CRUD complet)
# ==============================================================
@router.get("/agendas", summary="Lister tous les agendas")
def get_agendas():
    return service.get_all_agendas()

@router.get("/agendas/{agenda_id}", summary="Obtenir un agenda par ID")
def get_agenda(agenda_id: int):
    result = service.get_agenda(agenda_id)
    if not result:
        raise HTTPException(status_code=404, detail="Agenda introuvable")
    return result

@router.post("/agendas", summary="Créer un agenda", status_code=201)
def create_agenda(data: AgendaCreate):
    return service.create_agenda(data.model_dump(exclude_none=True))

@router.put("/agendas/{agenda_id}", summary="Mettre à jour un agenda")
def update_agenda(agenda_id: int, data: AgendaUpdate):
    payload = data.model_dump(exclude_none=True)
    if not payload:
        raise HTTPException(status_code=400, detail="Aucune donnée fournie")
    return service.update_agenda(agenda_id, payload)

@router.delete("/agendas/{agenda_id}", summary="Supprimer un agenda")
def delete_agenda(agenda_id: int):
    return service.delete_agenda(agenda_id)

# ==============================================================
# ENDPOINTS ACTIVITY (CRUD complet)
# ==============================================================
@router.get("/activities", summary="Lister toutes les activités")
def get_activities():
    return service.get_all_activities()

@router.get("/activities/{activity_id}", summary="Obtenir une activité par ID")
def get_activity(activity_id: int):
    result = service.get_activity(activity_id)
    if not result:
        raise HTTPException(status_code=404, detail="Activité introuvable")
    return result

@router.post("/activities", summary="Créer une activité", status_code=201)
def create_activity(data: ActivityCreate):
    return service.create_activity(data.model_dump(exclude_none=True))

@router.put("/activities/{activity_id}", summary="Mettre à jour une activité")
def update_activity(activity_id: int, data: ActivityUpdate):
    payload = data.model_dump(exclude_none=True)
    if not payload:
        raise HTTPException(status_code=400, detail="Aucune donnée fournie")
    return service.update_activity(activity_id, payload)

@router.delete("/activities/{activity_id}", summary="Supprimer une activité")
def delete_activity(activity_id: int):
    return service.delete_activity(activity_id)

# ==============================================================
# ENDPOINT RECONNAISSANCE FACIALE
# ==============================================================
@router.post("/identify-face", summary="Identifier une personne par reconnaissance faciale")
async def identify_face(file: UploadFile = File(...)):
    """
    Compare la photo aux enregistrements de la table <b>imageuser</b> (URL),
    résout le <b>nom</b> via <b>utilisateur.iduser</b>, ou retourne <code>inconnu</code>.

    Le calcul est CPU-bound (face_recognition + HOG) et sync — on le pousse
    en threadpool pour ne pas geler l'event loop pendant que d'autres routes
    (TTS, /audio/speech-to-action) tournent en parallèle au wake-word.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Le fichier doit être une image")
    image_bytes = await file.read()
    try:
        name = await asyncio.to_thread(service.identify_face, image_bytes)
        return {"nom": name}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la reconnaissance: {str(e)}")

# ==============================================================
# ENDPOINTS POWER ON / OFF
# ==============================================================
@router.post("/power-off", summary="Éteindre le système (etat = 0)")
def power_off():
    """
    Met le champ 'etat' dans la table setting à 0 (False).
    Signifie que le robot/distributeur est éteint.
    """
    return service.power_off()

@router.post("/power-on", summary="Allumer le système (etat = 1)")
def power_on():
    """
    Met le champ 'etat' dans la table setting à 1 (True).
    Signifie que le robot/distributeur est allumé.
    """
    return service.power_on()


# ==============================================================
# ENDPOINTS AUDIO (AZURE SPEECH)
# ==============================================================
@router.post("/audio/speech-to-text", summary="Convertir un fichier audio en texte")
async def speech_to_text(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="Le fichier doit être un audio")

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Le fichier audio est vide")

    try:
        # See speech_to_action: sync Azure SDK call → threadpool to keep the
        # event loop free for concurrent face_id / WS frames during a turn.
        return await asyncio.to_thread(service.speech_to_text, audio_bytes)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur Speech-to-Text: {str(e)}")


@router.post("/audio/text-to-speech", summary="Convertir du texte en audio")
def text_to_speech(payload: TextToSpeechRequest):
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Le texte ne doit pas être vide")

    try:
        audio_data = service.text_to_speech(payload.text, payload.voice_name)
        return StreamingResponse(
            iter([audio_data]),
            media_type="audio/wav",
            headers={"Content-Disposition": "inline; filename=tts.wav"}
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur Text-to-Speech: {str(e)}")


@router.post("/audio/speech-to-n8n-to-speech", summary="Audio -> texte -> n8n -> audio")
async def speech_to_n8n_to_speech(
    file: UploadFile = File(...),
    voice_name: str = Form(None),
    extra_text: str = Form(
        None,
        description="Texte ajouté entre parenthèses après la question STT, ex. « bonjour (oussema) »",
    ),
):
    if not file.content_type or not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="Le fichier doit être un audio")

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Le fichier audio est vide")

    try:
        # See speech_to_action above: run sync pipeline in a worker thread so
        # we don't block the event loop for the duration of the n8n round-trip.
        result = await asyncio.to_thread(
            service.audio_to_n8n_to_audio, audio_bytes, voice_name, extra_text,
        )
        return StreamingResponse(
            iter([result["audio_bytes"]]),
            media_type="audio/wav",
            headers={"Content-Disposition": "inline; filename=n8n_reply.wav"}
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        try:
            detail = f"Erreur pipeline audio n8n: {e!s}"
        except Exception:
            detail = "Erreur pipeline audio n8n."
        raise HTTPException(status_code=500, detail=detail)


@router.post(
    "/webhook/nom",
    summary="Greet par nom -> n8n -> action (TTS embarqué)",
)
async def webhook_nom(payload: NomGreetRequest):
    """Démarrage de conversation par la Pi après 5 min d'inactivité.

    Pipeline interne :
        nom -> n8n greet workflow -> traduction langue robot -> TTS -> JSON.

    La réponse JSON a exactement le même shape que ``/audio/speech-to-action``
    pour que la Pi puisse réutiliser son dispatcher d'action existant
    (action="text", audio_b64=WAV TTS, spoken_text, ...).

    Test rapide :
        curl -X POST http://127.0.0.1:8000/api/webhook/nom \\
             -H "Content-Type: application/json" \\
             -d '{"nom": "Salah"}'
    """
    nom = (payload.nom or "").strip()
    if not nom:
        raise HTTPException(status_code=400, detail="Le champ 'nom' est requis.")

    try:
        # Sync pipeline (translate + n8n + TTS) déplacé dans un worker thread
        # pour ne pas bloquer la boucle asyncio FastAPI.
        result = await asyncio.to_thread(
            service.name_to_action, nom, payload.voice_name,
        )
        audio_out = result.pop("audio_bytes", b"") or b""
        result["audio_b64"] = base64.b64encode(audio_out).decode("ascii") if audio_out else ""
        result["audio_format"] = "wav"
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        try:
            detail = f"Erreur pipeline greet: {e!s}"
        except Exception:
            detail = "Erreur pipeline greet."
        raise HTTPException(status_code=500, detail=detail)


@router.post(
    "/audio/speech-to-action",
    summary="Audio -> texte -> n8n -> action (text/music/motion/sleep) avec WAV embarqué",
)
async def speech_to_action(
    file: UploadFile = File(...),
    voice_name: str = Form(None),
    extra_text: str = Form(
        None,
        description="Texte ajouté entre parenthèses après la question STT (ex. utilisateur reconnu).",
    ),
    image: UploadFile = File(
        None,
        description="Photo (optionnelle) de la personne. Transmise à n8n quand la "
        "personne est inconnue, pour enregistrer un nouveau visage lors d'une présentation.",
    ),
):
    """
    Endpoint multi-type pour le robot KODA. La réponse JSON contient :
      - action: "text" | "music" | "motion" | "sleep" | "error"
      - spoken_text: texte parlé par le robot (dans la langue du robot)
      - audio_b64: WAV (base64) de `spoken_text` — toujours présent si spoken_text non vide
      - music_url, music_title: si action=music (URL YouTube à télécharger via yt-dlp côté Pi)
      - motion_command: si action=motion (forward/backward/left/right/stop)
      - input_text: ce que Azure STT a transcrit (utile pour log/debug côté Pi)
    """
    if not file.content_type or not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="Le fichier doit être un audio")

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Le fichier audio est vide")

    image_bytes = b""
    if image is not None:
        try:
            image_bytes = await image.read()
        except Exception:
            image_bytes = b""

    try:
        # Run the synchronous Azure-STT + n8n + Azure-TTS pipeline in a worker
        # thread. With the previous `service.audio_to_n8n_to_action(...)`
        # direct call inside an `async def` route, the whole pipeline (~5-30 s)
        # blocked the event loop and serialized every other HTTP request from
        # the Pi (face_id, TTS greeting, /trigger-n8n, even WebSocket frames).
        # Wrapping in to_thread restores true concurrency.
        result = await asyncio.to_thread(
            service.audio_to_n8n_to_action, audio_bytes, voice_name, extra_text,
            image_bytes or None,
        )
        audio_out = result.pop("audio_bytes", b"") or b""
        result["audio_b64"] = base64.b64encode(audio_out).decode("ascii") if audio_out else ""
        result["audio_format"] = "wav"
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        try:
            detail = f"Erreur pipeline audio->action: {e!s}"
        except Exception:
            detail = "Erreur pipeline audio->action."
        raise HTTPException(status_code=500, detail=detail)


# ==============================================================
# ENDPOINT WEBSOCKET — WAKE-WORD STREAMING (Pi → Azure STT)
# ==============================================================
_ws_logger = logging.getLogger("koda.ws.wake")


@router.websocket("/ws/wake-word/{robot_id}")
async def ws_wake_word(websocket: WebSocket, robot_id: str) -> None:
    """Streaming wake-word recognition over WebSocket.

    Protocol:
      1. Client connects, sends ONE JSON config frame as text::

            {"language": "ar-SA", "keywords": ["محسن", "mohsen", ...]}

      2. Client then sends raw S16_LE 16 kHz mono PCM bytes as binary frames.
      3. Server forwards bytes to Azure Speech `continuous_recognition` and
         streams events back to the client (see WakeWordStreamSession).
      4. Client can close at any time; we tear down the Azure session cleanly.
    """
    await websocket.accept()
    _ws_logger.info("WS wake-word OPEN robot_id=%s client=%s", robot_id, websocket.client)

    session: WakeWordStreamSession | None = None
    send_lock = asyncio.Lock()

    async def send_json(payload: dict) -> None:
        if websocket.application_state.name != "CONNECTED":
            return
        async with send_lock:
            try:
                await websocket.send_text(json.dumps(payload, ensure_ascii=False))
            except Exception:
                pass

    try:
        # 1) Read the config frame.
        config_raw = await websocket.receive_text()
        try:
            config = json.loads(config_raw)
        except json.JSONDecodeError as exc:
            await send_json({"event": "error", "message": f"bad config JSON: {exc}"})
            return
        language = str(config.get("language") or "ar-SA").strip()
        keywords = list(config.get("keywords") or [])
        if not keywords:
            await send_json({"event": "error", "message": "no keywords supplied"})
            return

        loop = asyncio.get_running_loop()
        session = WakeWordStreamSession(
            send_json,
            language=language,
            keywords=keywords,
            loop=loop,
        )
        try:
            await asyncio.to_thread(session.start)
        except Exception as exc:
            _ws_logger.exception("Failed to start Azure recognizer")
            await send_json({"event": "error", "message": f"azure start failed: {exc}"})
            return

        # 2) Forward incoming PCM frames until the client disconnects.
        pcm_chunks = 0
        pcm_bytes = 0
        last_pcm_log = time.perf_counter()
        while True:
            msg = await websocket.receive()
            if msg.get("type") == "websocket.disconnect":
                break
            data = msg.get("bytes")
            if data is None:
                # Could be a control text frame from the client (e.g. ping).
                continue
            pcm_chunks += 1
            pcm_bytes += len(data)
            now = time.perf_counter()
            if pcm_chunks == 1 or (now - last_pcm_log) >= 4.0:
                last_pcm_log = now
                _ws_logger.info(
                    "WS wake-word PCM robot_id=%s chunks=%d bytes=%d pcm_s=%.1f last_chunk=%d",
                    robot_id,
                    pcm_chunks,
                    pcm_bytes,
                    pcm_bytes / 32000.0,
                    len(data),
                )
            # Push the PCM in a worker thread to avoid blocking the event loop.
            await asyncio.to_thread(session.push_pcm, data)
    except WebSocketDisconnect:
        _ws_logger.info("WS wake-word DISCONNECT robot_id=%s", robot_id)
    except Exception:
        _ws_logger.exception("WS wake-word fatal error robot_id=%s", robot_id)
    finally:
        if session is not None:
            await asyncio.to_thread(session.close)
        try:
            await websocket.close()
        except Exception:
            pass
        _ws_logger.info("WS wake-word CLOSED robot_id=%s", robot_id)


# ==============================================================
# ENDPOINT GEMINI KEYWORDS (ROBOT NAME)
# ==============================================================
@router.get("/keywords/robot-name", summary="Générer les variantes du nom du robot via Gemini")
def get_robot_name_keywords():
    try:
        return service.generate_robot_name_keywords()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur Gemini keywords: {str(e)}")


# ==============================================================
# DÉCLENCHEUR NOCTURNE — webhook n8n par utilisateur (00:00)
# ==============================================================
@router.post(
    "/triggers/nightly-users",
    summary="Déclencher manuellement le webhook n8n pour chaque utilisateur",
)
def trigger_nightly_users_manual():
    """
    Test manuel : récupère tous les utilisateurs de la table ``utilisateur``
    et appelle le webhook n8n une fois par nom (ex. ?user=oussema, ?user=salah).
    Même logique que le job automatique de minuit.
    """
    try:
        return service.run_nightly_user_webhook_trigger()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur déclencheur nocturne: {str(e)}")


@router.get(
    "/triggers/nightly-users/status",
    summary="État du scheduler du déclencheur nocturne",
)
def get_nightly_users_trigger_status():
    return get_scheduler_status()
