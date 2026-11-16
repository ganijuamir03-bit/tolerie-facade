"""
Générateur STEP 3D du profil plié — brique 4.

Construit la section pliée à partir des faces (cotes extérieures) et des plis
(angle + sens), coins arrondis au rayon de pli, puis extrude sur la longueur.
Export STEP (AP214) via le noyau OpenCASCADE (build123d).

Le STEP est un modèle 3D de référence (visualisation, assemblage, contrôle).
La mise à plat de découpe reste pilotée par la table maison (voir dxf.py).
"""
from __future__ import annotations
import math

from build123d import (BuildSketch, BuildLine, Polyline, Line, fillet, trace,
                       extrude, export_step)

from .profil import Profil


def generer_step(profil: Profil, chemin: str,
                 rayon_interieur: float | None = None) -> dict:
    t = profil.epaisseur
    if not t:
        raise ValueError("Épaisseur manquante pour le STEP.")
    L = profil.longueur
    if not L:
        raise ValueError("Longueur de pièce manquante (sens d'extrusion).")
    faces = profil.faces
    if len(faces) < 1:
        raise ValueError("Profil sans face.")

    r = rayon_interieur if rayon_interieur is not None else t   # défaut : r = t
    Rc = r + t / 2.0                                            # rayon centerline

    # apex de la polyligne centerline à partir des cotes extérieures
    pts = [(0.0, 0.0)]
    x = y = 0.0
    ang = 0.0
    for i, f in enumerate(faces):
        x += f * math.cos(math.radians(ang))
        y += f * math.sin(math.radians(ang))
        pts.append((x, y))
        if i < len(profil.plis):
            pli = profil.plis[i]
            signe = +1.0 if pli.sens.upper().startswith("V") else -1.0
            ang += pli.angle * signe

    with BuildSketch() as sk:
        with BuildLine() as ln:
            if len(pts) >= 2:
                Polyline(*pts)
            else:
                Line(pts[0], (pts[0][0] + 1, pts[0][1]))
            if len(pts) >= 3 and Rc > 0:
                try:
                    fillet(ln.vertices(), radius=Rc)   # arrondit les plis
                except Exception:
                    pass  # si rayon trop grand pour une face, on garde l'angle vif
        trace(line_width=t)
    part = extrude(sk.sketch, amount=L)

    export_step(part, chemin)
    bb = part.bounding_box()
    return {
        "chemin": chemin,
        "matiere": profil.matiere,
        "epaisseur": t,
        "rayon_interieur": r,
        "longueur": L,
        "nb_plis": profil.nb_plis,
        "volume_mm3": round(part.volume, 1),
        "masse_estimee_kg": _masse(profil.matiere, part.volume),
        "bbox_mm": (round(bb.size.X, 2), round(bb.size.Y, 2), round(bb.size.Z, 2)),
    }


# masses volumiques indicatives (kg/dm3) pour une estimation de poids
_RHO = {"inox": 7.9, "acier": 7.85, "alu": 2.70, "aluminium": 2.70,
        "laiton": 8.4, "cuivre": 8.9, "galva": 7.85, "zincor": 7.85}


def _masse(matiere: str, volume_mm3: float) -> float | None:
    m = (matiere or "").lower()
    for cle, rho in _RHO.items():
        if cle in m:
            return round(volume_mm3 * rho / 1e6, 3)  # dm3 (=mm3/1e6) * kg/dm3
    return None
