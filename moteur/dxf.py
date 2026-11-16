"""
Générateur DXF du flan déplié — brique 3.

Déterministe et autonome : à partir d'un Profil (faces/plis + matière) et
d'une liste de features (trous, oblongs, découpes), produit un DXF propre,
en millimètres, avec des couches séparées :

    CONTOUR   contour extérieur du flan (découpe)
    PERCAGE   trous ronds, oblongs, découpes intérieures (découpe)
    PLIS      lignes de pliage (repère, NON découpé, trait tireté)
    COTATION  textes d'info (matière, matrice, cotes)

Repère : X = longueur de la pièce (sens d'extrusion), Y = largeur dépliée.
Les lignes de pli sont parallèles à X, placées en Y au déplié, selon la
convention « demi-déduction de chaque côté du pli » (exacte pour cotes ext.).
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field

import ezdxf

from .profil import Profil
from .table_pliage import TablePliage


# ------- features placées sur le flan (coordonnées X=longueur, Y=largeur) ----
@dataclass
class Trou:
    x: float; y: float; diametre: float

@dataclass
class Oblong:
    x: float; y: float; longueur: float; largeur: float; angle: float = 0.0  # deg

@dataclass
class DecoupeRect:
    x: float; y: float; largeur: float; hauteur: float   # coin bas-gauche

@dataclass
class PieceAPlat:
    profil: Profil
    features: list = field(default_factory=list)
    contour: list[tuple[float, float]] | None = None  # None => rectangle L×W

    def calcul(self, table: TablePliage) -> dict:
        d = self.profil.deplie(table)
        W = d["largeur_deplie"]
        L = self.profil.longueur
        if not L:
            raise ValueError("Longueur de pièce manquante (sens d'extrusion).")
        # positions des lignes de pli en Y : y_k = Σfaces(≤k) − (k−0.5)·BD
        bd = d["deduction_unitaire"]
        faces = d["faces"]
        plis_y, cum = [], 0.0
        for k in range(1, len(faces)):
            cum += faces[k - 1]
            plis_y.append(round(cum - (k - 0.5) * bd, 4))
        d.update({"L": L, "W": W, "plis_y": plis_y})
        return d


# ------- helpers géométrie ----------------------------------------------------
def _ajouter_oblong(msp, ob: Oblong, layer: str):
    a = math.radians(ob.angle)
    ux, uy = math.cos(a), math.sin(a)      # axe du slot
    vx, vy = -math.sin(a), math.cos(a)     # perpendiculaire
    h = (ob.longueur - ob.largeur) / 2.0   # demi-longueur droite
    if h < 0:
        raise ValueError("Oblong : longueur doit être ≥ largeur.")
    r = ob.largeur / 2.0
    C1 = (ob.x - h * ux, ob.y - h * uy)
    C2 = (ob.x + h * ux, ob.y + h * uy)
    A = (C1[0] + r * vx, C1[1] + r * vy)
    B = (C2[0] + r * vx, C2[1] + r * vy)
    D = (C2[0] - r * vx, C2[1] - r * vy)
    E = (C1[0] - r * vx, C1[1] - r * vy)
    # polyligne fermée avec deux demi-cercles (bulge = 1)
    msp.add_lwpolyline(
        [(A[0], A[1], 0), (B[0], B[1], 1.0), (D[0], D[1], 0), (E[0], E[1], 1.0)],
        format="xyb", close=True, dxfattribs={"layer": layer},
    )


def generer_dxf(piece: PieceAPlat, table: TablePliage, chemin: str) -> dict:
    d = piece.calcul(table)
    L, W = d["L"], d["W"]

    doc = ezdxf.new("R2010", setup=True)   # setup=True => linetypes standard
    doc.units = ezdxf.units.MM
    doc.layers.add("CONTOUR", color=7)
    doc.layers.add("PERCAGE", color=1)
    doc.layers.add("PLIS", color=5, linetype="DASHED")
    doc.layers.add("COTATION", color=3)
    msp = doc.modelspace()

    # contour
    pts = piece.contour or [(0, 0), (L, 0), (L, W), (0, W)]
    msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "CONTOUR"})

    # lignes de pli (parallèles à X)
    for y in d["plis_y"]:
        msp.add_line((0, y), (L, y), dxfattribs={"layer": "PLIS"})

    # features
    for f in piece.features:
        if isinstance(f, Trou):
            msp.add_circle((f.x, f.y), f.diametre / 2.0, dxfattribs={"layer": "PERCAGE"})
        elif isinstance(f, Oblong):
            _ajouter_oblong(msp, f, "PERCAGE")
        elif isinstance(f, DecoupeRect):
            msp.add_lwpolyline(
                [(f.x, f.y), (f.x + f.largeur, f.y),
                 (f.x + f.largeur, f.y + f.hauteur), (f.x, f.y + f.hauteur)],
                close=True, dxfattribs={"layer": "PERCAGE"})

    # cartouche d'info (hors pièce, en bas)
    info = (f"{piece.profil.titre or 'Pièce'}  |  {d['matiere']} {d['epaisseur']}mm  |  "
            f"matrice {d['matrice']}  déduction {d['deduction_unitaire']}mm/pli  |  "
            f"déplié {W}mm x long {L}mm  |  {d['nb_plis']} plis")
    msp.add_text(info, height=max(W * 0.04, 6),
                 dxfattribs={"layer": "COTATION"}).set_placement((0, -max(W * 0.12, 20)))

    doc.saveas(chemin)
    d["chemin"] = chemin
    return d
