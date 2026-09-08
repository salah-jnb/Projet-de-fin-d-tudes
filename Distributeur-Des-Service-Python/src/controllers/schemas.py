from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ---- AGENDA ----
class AgendaCreate(BaseModel):
    titre: str
    note: str
    etat: bool = False
    contenu: str
    date_modification: Optional[datetime] = None


class AgendaUpdate(BaseModel):
    titre: Optional[str] = None
    note: Optional[str] = None
    etat: Optional[bool] = None
    contenu: Optional[str] = None
    date_modification: Optional[datetime] = None


# ---- NOTE / ACTIVITÉS (table note) ----
class ActivityCreate(BaseModel):
    note: str
    etat: bool = False
    date: Optional[datetime] = None


class ActivityUpdate(BaseModel):
    note: Optional[str] = None
    etat: Optional[bool] = None
    date: Optional[datetime] = None


class NoteCreate(BaseModel):
    note: str
    etat: bool = False
    date: Optional[datetime] = None


class NoteUpdate(BaseModel):
    note: Optional[str] = None
    etat: Optional[bool] = None
    date: Optional[datetime] = None


# ---- SETTING ----
class SettingUpdate(BaseModel):
    name: Optional[str] = None
    sexe: Optional[str] = None
    date: Optional[str] = None
    motdepasse: Optional[str] = None
    etat: Optional[bool] = None
    caractere: Optional[str] = None
    langue: Optional[str] = None


# ---- AUDIO ----
class TextToSpeechRequest(BaseModel):
    text: str
    voice_name: Optional[str] = None


# ---- WEBHOOK GREET (passive 5-min idle wake) ----
class NomGreetRequest(BaseModel):
    nom: str = Field(..., min_length=1, max_length=120, description="Nom de l'utilisateur reconnu (ou 'inconnu')")
    voice_name: Optional[str] = None


# ---- UTILISATEUR ----
class UtilisateurCreate(BaseModel):
    nom: str
    idkoda: str = ""


class UtilisateurUpdate(BaseModel):
    nom: Optional[str] = None
    idkoda: Optional[str] = None


# ---- IMAGE UTILISATEUR (reconnaissance faciale, etc.) ----
class ImageUserCreate(BaseModel):
    iduser: int
    url: str


class ImageUserUpdate(BaseModel):
    iduser: Optional[int] = None
    url: Optional[str] = None


# ---- ACCOMPAGNEMENT ----
class AccompagnementCreate(BaseModel):
    interets: str = ""
    synthese: str = ""
    point_cles: str = ""
    conseils: str = ""
    iduser: int


class AccompagnementUpdate(BaseModel):
    interets: Optional[str] = None
    synthese: Optional[str] = None
    point_cles: Optional[str] = None
    conseils: Optional[str] = None
    iduser: Optional[int] = None


# ---- CONVERSATION ----
class ConversationCreate(BaseModel):
    question: str
    reponce: str = ""
    typedequestion: str = ""
    iduser: int
    date: Optional[datetime] = None


class ConversationUpdate(BaseModel):
    question: Optional[str] = None
    reponce: Optional[str] = None
    typedequestion: Optional[str] = None
    iduser: Optional[int] = None
    date: Optional[datetime] = None


# ---- HISTORIQUE ----
class HistoriqueCreate(BaseModel):
    question: str
    reponce: str = ""
    type_question: str = ""


# ---- INFORMATION PERSONNELLE ----
class InformationPersonelleCreate(BaseModel):
    question: str
    reponce: str = ""
    iduser: int
    date: Optional[datetime] = None


class InformationPersonelleUpdate(BaseModel):
    question: Optional[str] = None
    reponce: Optional[str] = None
    iduser: Optional[int] = None
    date: Optional[datetime] = None


# ---- AUTHENTIFICATION ----
class AuthentificationCreate(BaseModel):
    idproduit: int = Field(..., description="Identifiant produit (clé métier)")
    emailclient: str
    motdepasse: str
    idkoda: str = ""


class AuthentificationUpdate(BaseModel):
    emailclient: Optional[str] = None
    motdepasse: Optional[str] = None
    idkoda: Optional[str] = None


class LoginRequest(BaseModel):
    emailclient: str
    motdepasse: str
