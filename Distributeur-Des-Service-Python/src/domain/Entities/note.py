from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Note:
    id: int
    note: str
    etat: bool
    date: Optional[datetime] = None
