from dataclasses import dataclass


@dataclass
class Utilisateur:
    """Table utilisateur — les photos de profil / reconnaissance sont dans <c>imageuser</c>."""

    iduser: int
    nom: str
    idkoda: str
