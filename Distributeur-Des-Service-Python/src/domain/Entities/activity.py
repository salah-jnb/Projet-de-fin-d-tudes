from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Activity:
    """
    Alias métier pour une entrée de la table `note` (note, etat, date).
    Conservé pour compatibilité avec les routes /activities existantes.
    """

    id: int
    note: str
    etat: bool
    date: Optional[datetime] = None
