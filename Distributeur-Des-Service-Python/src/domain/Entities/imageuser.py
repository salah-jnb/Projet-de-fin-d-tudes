from dataclasses import dataclass


@dataclass
class ImageUser:
    """Table imageuser — URLs des images utilisateur liées à <c>utilisateur.iduser</c>."""

    idimage: int
    iduser: int
    url: str
