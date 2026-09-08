from dataclasses import dataclass


@dataclass
class Authentification:
    """Table authentification (<c>idproduit</c> / idProduit côté SQL)."""

    idproduit: int
    emailclient: str
    motdepasse: str
    idkoda: str
