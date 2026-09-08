from dataclasses import dataclass
from datetime import datetime


@dataclass
class InformationPersonelle:
    id: int
    question: str
    reponce: str
    date: datetime
    iduser: int
