"""
Lecture d'un plan PDF client (vectoriel) — brique 2.

Étape A (ce module) : extraction du CARTOUCHE par proximité label -> valeur.
Les gabarits diffèrent d'un client à l'autre, donc on procède par
« je cherche la valeur la plus proche à droite ou en dessous du libellé ».

Renvoie un dict de champs : matiere, epaisseur, longueur, position,
quantite, traitement, entre_axe, titre.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field

import pymupdf


@dataclass
class Mot:
    x0: float; y0: float; x1: float; y1: float; txt: str
    @property
    def cx(self): return (self.x0 + self.x1) / 2
    @property
    def cy(self): return (self.y0 + self.y1) / 2
    @property
    def h(self): return self.y1 - self.y0


# libellés du cartouche -> clé normalisée. On accepte les variantes.
LABELS = {
    "matiere":   [r"mati[eè]re"],
    "position":  [r"\bpos\b", r"position"],
    "longueur":  [r"longueur"],
    "quantite":  [r"quantit[eé]", r"\bqt[eé]?\b", r"\bpi?[eè]ces?\b"],
    "traitement":[r"traitement", r"finition"],
    "entre_axe": [r"entre[-\s]?axe"],
}


def _mots_page(page) -> list[Mot]:
    out = []
    for w in page.get_text("words"):
        x0, y0, x1, y1, txt = w[0], w[1], w[2], w[3], w[4]
        if txt.strip():
            out.append(Mot(x0, y0, x1, y1, txt.strip()))
    return out


def _ligne_de(mots: list[Mot], ref: Mot, tol=None) -> list[Mot]:
    """Mots sur la même ligne que ref (recouvrement vertical), triés par x."""
    tol = tol if tol is not None else max(ref.h * 0.6, 2.0)
    same = [m for m in mots if abs(m.cy - ref.cy) <= tol]
    return sorted(same, key=lambda m: m.x0)


def _valeur_apres_label(mots: list[Mot], label: Mot) -> str | None:
    """Valeur à droite du label sur la même ligne ; sinon ligne juste en dessous."""
    # 1) à droite, même ligne
    ligne = _ligne_de(mots, label)
    droite = [m for m in ligne if m.x0 >= label.x1 - 1 and m is not label]
    droite = [m for m in droite if not _est_label(m.txt)]
    if droite:
        return " ".join(m.txt for m in droite).strip(" :")
    # 2) ligne juste en dessous, aligné en x (dans la largeur du label +/-)
    dessous = [m for m in mots
               if label.y1 - 1 <= m.y0 <= label.y1 + label.h * 2.2
               and m.x1 >= label.x0 - 5 and m.x0 <= label.x1 + 120]
    if dessous:
        yref = min(m.y0 for m in dessous)
        band = [m for m in dessous if abs(m.y0 - yref) <= max(label.h * 0.6, 2)]
        band = [m for m in band if not _est_label(m.txt)]
        if band:
            return " ".join(m.txt for m in sorted(band, key=lambda m: m.x0)).strip(" :")
    return None


def _est_label(txt: str) -> bool:
    t = txt.lower()
    for pats in LABELS.values():
        for p in pats:
            if re.fullmatch(p + r"\s*:?", t):
                return True
    return False


def _match_label(txt: str) -> str | None:
    t = txt.lower().rstrip(":").strip()
    for cle, pats in LABELS.items():
        for p in pats:
            if re.fullmatch(p, t):
                return cle
    return None


def _extraire_epaisseur(matiere: str | None) -> float | None:
    if not matiere:
        return None
    m = re.search(r"(\d+[.,]?\d*)\s*mm", matiere, re.I)
    if m:
        return float(m.group(1).replace(",", "."))
    return None


def lire_cartouche(chemin_pdf: str) -> dict:
    doc = pymupdf.open(chemin_pdf)
    champs = {k: None for k in
              ["titre", "matiere", "epaisseur", "longueur",
               "position", "quantite", "traitement", "entre_axe"]}

    for page in doc:
        mots = _mots_page(page)
        # titre = plus long texte contenant un mot-clé de pièce, sur la page 1
        if champs["titre"] is None:
            for m in mots:
                pass  # (titre traité plus bas via lignes)
        # repérer les labels et leurs valeurs
        for m in mots:
            cle = _match_label(m.txt)
            if cle and champs.get(cle) in (None, ""):
                val = _valeur_apres_label(mots, m)
                if val:
                    champs[cle] = val
        # titre : une ligne contenant un type de pièce connu
        TYPES = r"(couvertine|tablette|bavette|larmier|corni[eè]re|profil|t[oô]le|sous[-\s]?construction|fermeture)"
        if champs["titre"] is None:
            lignes = {}
            for m in mots:
                lignes.setdefault(round(m.cy), []).append(m)
            for y, ms in lignes.items():
                texte = " ".join(x.txt for x in sorted(ms, key=lambda a: a.x0))
                if re.search(TYPES, texte, re.I) and len(texte) > 12:
                    champs["titre"] = texte
                    break

    champs["epaisseur"] = _extraire_epaisseur(champs.get("matiere"))
    # longueur -> nombre
    if champs.get("longueur"):
        mm = re.search(r"(\d+[.,]?\d*)", champs["longueur"])
        champs["longueur_mm"] = float(mm.group(1).replace(",", ".")) if mm else None
    return champs


if __name__ == "__main__":
    import sys, json
    d = lire_cartouche(sys.argv[1])
    print(json.dumps(d, ensure_ascii=False, indent=2))
