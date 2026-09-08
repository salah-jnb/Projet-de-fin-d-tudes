from dataclasses import dataclass


@dataclass
class Accompagnement:
    id: int
    interets: str
    synthese: str
    point_cles: str
    conseils: str
    iduser: int
