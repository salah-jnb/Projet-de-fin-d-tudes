from dataclasses import dataclass


@dataclass
class Setting:
    """Table setting (schéma métier : clé primaire <c>id</c>)."""

    id: int
    name: str
    sexe: str
    date: str
    motdepasse: str
    etat: bool
    caractere: str
    langue: str = ""
