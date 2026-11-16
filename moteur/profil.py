"""
Modèle « Profil » et calcul de déplié — cœur commun aux deux sources
(plans de pièce et devis/plans d'ensemble).

Un profil à section constante = une suite de FACES (longueurs extérieures)
reliées par des PLIS (angles). Le déplié se calcule :

    largeur_déplié = Σ(faces extérieures) − Σ(déductions de pli)

où la déduction vient de la table maison selon matière / épaisseur / matrice.
Convention cotation : cotes EXTÉRIEURES (comme sur vos plans).
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field

from .table_pliage import TablePliage


@dataclass
class Pli:
    angle: float = 90.0        # angle de pliage en degrés (90 = équerre)
    sens: str = "V"            # "V" (vallée) ou "M" (montagne) — info pour plus tard


@dataclass
class Profil:
    faces: list[float]                 # longueurs extérieures des faces [mm]
    plis: list[Pli] = field(default_factory=list)   # len(plis) == len(faces)-1
    matiere: str = ""
    epaisseur: float = 0.0
    longueur: float | None = None      # longueur de la pièce (sens extrusion) [mm]
    matrice: str | None = None         # None => choisie automatiquement
    titre: str = ""
    position: str = ""

    def __post_init__(self):
        if not self.plis and len(self.faces) >= 2:
            self.plis = [Pli() for _ in range(len(self.faces) - 1)]

    @property
    def nb_plis(self) -> int:
        return len(self.plis)

    def resoudre_matrice(self, table: TablePliage) -> str:
        if self.matrice:
            return self.matrice
        m = table.matrice_par_defaut(self.matiere, self.epaisseur)
        if not m:
            raise ValueError(
                f"Aucune matrice avec déduction pour {self.matiere} {self.epaisseur}mm "
                f"(table incomplète — voir Julien)."
            )
        return m

    def deplie(self, table: TablePliage) -> dict:
        """Calcule la largeur dépliée + le détail, à partir de la table maison."""
        matrice = self.resoudre_matrice(table)
        ded = table.deduction(self.matiere, self.epaisseur, matrice)
        somme_faces = sum(self.faces)
        largeur = somme_faces - self.nb_plis * ded
        return {
            "matiere": self.matiere,
            "epaisseur": self.epaisseur,
            "matrice": matrice,
            "faces": list(self.faces),
            "nb_plis": self.nb_plis,
            "deduction_unitaire": ded,
            "somme_faces": round(somme_faces, 3),
            "largeur_deplie": round(largeur, 3),
            "longueur": self.longueur,
        }


# --- parsing des chaînes de cotes de profil (devis / plans d'ensemble) --------

def parser_faces(chaine: str) -> list[float]:
    """
    '64+35+80+160+80+40' -> [64,35,80,160,80,40]
    Accepte aussi '64 + 35 + 80', virgules décimales, et ignore le reste.
    """
    # garde uniquement les nombres séparés par +
    m = re.search(r"\d[\d.,]*(?:\s*\+\s*\d[\d.,]*)+", chaine)
    if not m:
        return []
    bloc = m.group(0)
    return [float(x.replace(",", ".")) for x in re.split(r"\s*\+\s*", bloc)]


def profil_depuis_chaine(chaine: str, matiere: str, epaisseur: float,
                         longueur: float | None = None, **kw) -> Profil:
    faces = parser_faces(chaine)
    if len(faces) < 2:
        raise ValueError(f"Chaîne de faces non reconnue : {chaine!r}")
    return Profil(faces=faces, matiere=matiere, epaisseur=epaisseur,
                  longueur=longueur, **kw)
