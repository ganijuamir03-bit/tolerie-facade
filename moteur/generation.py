"""
Orchestrateur de génération — relie le formulaire aux générateurs.

Entrée : un dict de paramètres (matière, épaisseur, faces, plis, features,
options DXF/STEP). Sortie : fichiers produits + récap du déplié.
"""
from __future__ import annotations
import os
import re

from .table_pliage import TablePliage
from .profil import Profil, Pli, parser_faces
from .dxf import PieceAPlat, Trou, Oblong, DecoupeRect, generer_dxf
from .step3d import generer_step


def _slug(s: str) -> str:
    s = re.sub(r"[^\w\-]+", "_", (s or "piece").strip())
    return s.strip("_") or "piece"


def construire_profil(p: dict) -> Profil:
    # faces : liste directe ou chaîne "64+35+80"
    faces = p.get("faces")
    if not faces and p.get("faces_str"):
        faces = parser_faces(p["faces_str"])
    faces = [float(x) for x in (faces or [])]
    if len(faces) < 1:
        raise ValueError("Aucune face : saisis au moins une cote (ex. 64+35+80).")

    plis = []
    plis_in = p.get("plis")
    if plis_in:
        for d in plis_in:
            plis.append(Pli(angle=float(d.get("angle", 90)), sens=d.get("sens", "V")))
    # sinon Profil complète automatiquement avec des plis 90° V

    return Profil(
        faces=faces, plis=plis,
        matiere=p.get("matiere", ""),
        epaisseur=float(p.get("epaisseur") or 0),
        longueur=float(p["longueur"]) if p.get("longueur") else None,
        matrice=p.get("matrice") or None,
        titre=p.get("titre", ""), position=p.get("position", ""),
    )


def construire_features(liste: list[dict]) -> list:
    out = []
    for f in liste or []:
        typ = (f.get("type") or "").lower()
        if typ == "trou":
            out.append(Trou(float(f["x"]), float(f["y"]), float(f["diametre"])))
        elif typ == "oblong":
            out.append(Oblong(float(f["x"]), float(f["y"]), float(f["longueur"]),
                              float(f["largeur"]), float(f.get("angle", 0))))
        elif typ in ("decoupe", "decoupe_rect", "rect"):
            out.append(DecoupeRect(float(f["x"]), float(f["y"]),
                                   float(f["largeur"]), float(f["hauteur"])))
    return out


def generer(params: dict, table: TablePliage, dossier: str,
            faire_apercu: bool = True) -> dict:
    os.makedirs(dossier, exist_ok=True)
    profil = construire_profil(params)
    features = construire_features(params.get("features"))
    options = params.get("options") or {"dxf": True, "step": True}
    base = _slug(params.get("titre") or params.get("position") or "piece")

    res = {"base": base, "fichiers": {}, "apercus": {}, "avertissements": []}

    # déplié (toujours calculé) — peut lever si table incomplète
    try:
        res["deplie"] = profil.deplie(table)
    except Exception as e:
        res["deplie"] = None
        res["avertissements"].append(f"Déplié : {e}")

    # DXF
    if options.get("dxf"):
        piece = PieceAPlat(profil=profil, features=features)
        dxf_path = os.path.join(dossier, base + ".dxf")
        res["infos_dxf"] = generer_dxf(piece, table, dxf_path)
        res["fichiers"]["dxf"] = dxf_path
        if faire_apercu:
            from .apercu import apercu_dxf
            png = os.path.join(dossier, base + "_dxf.png")
            apercu_dxf(dxf_path, png); res["apercus"]["dxf"] = png

    # STEP
    if options.get("step"):
        step_path = os.path.join(dossier, base + ".step")
        rayon = params.get("rayon_interieur")
        res["infos_step"] = generer_step(
            profil, step_path,
            rayon_interieur=float(rayon) if rayon else None)
        res["fichiers"]["step"] = step_path
        if faire_apercu:
            from .apercu import apercu_step
            png = os.path.join(dossier, base + "_step.png")
            apercu_step(step_path, png, titre=base); res["apercus"]["step"] = png

    return res
