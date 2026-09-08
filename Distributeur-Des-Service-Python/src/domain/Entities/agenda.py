from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Agenda:
    """Table agenda : nom de colonne date côté SQL <c>date_modifiction</c> (orthographe base)."""

    id: int
    titre: str
    note: str
    etat: bool
    contenu: str
    date_modifiction: Optional[datetime] = None
