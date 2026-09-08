from dataclasses import dataclass
from datetime import datetime


@dataclass
class Conversation:
    id: int
    question: str
    reponce: str
    date: datetime
    typedequestion: str
    iduser: int
