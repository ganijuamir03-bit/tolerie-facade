"""
Lecture de la table de pliage (facteur K + déduction) depuis le fichier Excel
« aide_pour_dessinateur.xlsx », feuille « tableau facteur K et déduction ».

Produit une structure interrogeable :
    table.deduction(matiere, epaisseur, matrice) -> float (mm)
    table.facteur_k(matiere, epaisseur, matrice) -> float

Les matrices sont normalisées en familles : M6, M8, M10, M12, M16, M20, M24.
"""
from __future__ import annotations
import json
import re
import unicodedata
from dataclasses import dataclass, field, asdict

import openpyxl

# Colonnes (1=A) : pour chaque matrice -> (col facteur K, col deduction)
MATRICES = {
    "M6":  (3, 4),    # C / D  (M6-90°)
    "M8":  (5, 6),    # E / F  (M8-90°)
    "M10": (7, 8),    # G / H  (M10-35°)
    "M12": (9, 10),   # I / J  (M12-90°)
    "M16": (11, 12),  # K / L  (M16-35)
    "M20": (13, 14),  # M / N  (M20-90°sp)
    "M24": (15, 16),  # O / P  (M24-35°)
}

SHEET = "tableau facteur K et déduction"


def _norm(s: str) -> str:
    """Minuscule, sans accents, espaces compactés : pour comparer des libellés."""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()


def _num(v):
    """Convertit '3,4' / '0.46' / 3.4 / '???' en float ou None."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", ".")
    if not s or "?" in s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


@dataclass
class GroupeMatiere:
    nom: str                      # libellé complet de la ligne d'en-tête
    # valeurs[epaisseur][matrice] = {"k": ..., "deduction": ...}
    valeurs: dict = field(default_factory=dict)


class TablePliage:
    def __init__(self, groupes: dict[str, GroupeMatiere], source: str = ""):
        self.groupes = groupes
        self.source = source

    # --- construction depuis l'Excel ---------------------------------------
    @classmethod
    def depuis_excel(cls, chemin: str) -> "TablePliage":
        wb = openpyxl.load_workbook(chemin, data_only=True)
        ws = wb[SHEET]
        groupes: dict[str, GroupeMatiere] = {}

        r = 1
        maxr = ws.max_row
        while r <= maxr:
            a = ws.cell(row=r, column=1).value
            # en-tête de matière = texte en colonne A qui n'est pas "Epaisseur"
            if isinstance(a, str) and a.strip() and _norm(a) != "epaisseur":
                nom = a.strip()
                g = GroupeMatiere(nom=nom)
                # lignes de données = celles ou la colonne B (epaisseur) est un nombre,
                # jusqu'au prochain en-tete de matiere.
                rr = r + 1
                while rr <= maxr:
                    a2 = ws.cell(row=rr, column=1).value
                    if isinstance(a2, str) and a2.strip() and _norm(a2) != "epaisseur":
                        break  # nouveau groupe
                    ep = _num(ws.cell(row=rr, column=2).value)
                    if ep is not None:
                        cases = {}
                        for fam, (ck, cd) in MATRICES.items():
                            k = _num(ws.cell(row=rr, column=ck).value)
                            d = _num(ws.cell(row=rr, column=cd).value)
                            if k is not None or d is not None:
                                cases[fam] = {"k": k, "deduction": d}
                        if cases:
                            g.valeurs[ep] = cases
                    rr += 1
                if g.valeurs:
                    groupes[nom] = g
                r = rr
            else:
                r += 1
        return cls(groupes, source=chemin)

    # --- recherche de matière tolérante -------------------------------------
    def chercher_matiere(self, matiere: str) -> str | None:
        """Retourne la clé de groupe correspondant le mieux à une matière saisie."""
        q = _norm(matiere)
        # 1) correspondance directe sur mots-clés connus
        alias = {
            "inox": "inox 1.4301",
            "1.4301": "inox 1.4301",
            "1.4404": "inox 1.4301",
            "alu": "aluminium pe100",
            "aluminium": "aluminium pe100",
            "5005": "aluminium pe100",
            "acier 52": "acier 52",
            "s355": "acier 52",
            "acier 37": "acier 37",
            "s235": "acier 37",
            "dc01": "acier 37",
            "laiton": "laiton",
            "cuivre": "cuivre",
        }
        cible = None
        for mot, cle in alias.items():
            if mot in q:
                cible = cle
                break
        for nom in self.groupes:
            n = _norm(nom)
            if cible and cible in n:
                return nom
        # 2) sinon : le groupe dont le nom partage le plus de mots
        best, best_score = None, 0
        for nom in self.groupes:
            n = _norm(nom)
            score = sum(1 for w in q.split() if w in n)
            if score > best_score:
                best, best_score = nom, score
        return best

    def _case(self, matiere: str, epaisseur: float, matrice: str):
        nom = self.chercher_matiere(matiere)
        if nom is None:
            raise KeyError(f"Matière introuvable : {matiere!r}")
        g = self.groupes[nom]
        fam = matrice.upper().split("X")[0].split("-")[0].strip()
        fam = re.match(r"M\d+", fam)
        fam = fam.group(0) if fam else matrice.upper()
        if epaisseur not in g.valeurs:
            dispo = sorted(g.valeurs)
            raise KeyError(f"Épaisseur {epaisseur} absente pour {nom}. Dispo: {dispo}")
        if fam not in g.valeurs[epaisseur]:
            dispo = sorted(g.valeurs[epaisseur])
            raise KeyError(f"Matrice {fam} absente pour {nom} {epaisseur}mm. Dispo: {dispo}")
        return nom, fam, g.valeurs[epaisseur][fam]

    def deduction(self, matiere: str, epaisseur: float, matrice: str) -> float:
        _, _, c = self._case(matiere, epaisseur, matrice)
        if c["deduction"] is None:
            raise ValueError("Déduction non renseignée dans la table (voir Julien).")
        return c["deduction"]

    def facteur_k(self, matiere: str, epaisseur: float, matrice: str) -> float:
        _, _, c = self._case(matiere, epaisseur, matrice)
        if c["k"] is None:
            raise ValueError("Facteur K non renseigné dans la table.")
        return c["k"]

    def matrices_disponibles(self, matiere: str, epaisseur: float) -> list[dict]:
        """Matrices ayant une déduction renseignée pour cette matière/épaisseur."""
        nom = self.chercher_matiere(matiere)
        if nom is None or epaisseur not in self.groupes[nom].valeurs:
            return []
        cases = self.groupes[nom].valeurs[epaisseur]
        res = []
        for fam, c in cases.items():
            if c.get("deduction") is not None:
                res.append({"matrice": fam, "deduction": c["deduction"], "k": c["k"]})
        # ordre par taille de matrice (M6 < M8 < ... < M24)
        res.sort(key=lambda d: int(re.sub(r"\D", "", d["matrice"]) or 0))
        return res

    def matrice_par_defaut(self, matiere: str, epaisseur: float) -> str | None:
        """Choix par défaut : la plus petite matrice valide (modifiable par l'opérateur)."""
        dispo = self.matrices_disponibles(matiere, epaisseur)
        return dispo[0]["matrice"] if dispo else None

    def exporter_json(self, chemin: str):
        data = {nom: asdict(g) for nom, g in self.groupes.items()}
        with open(chemin, "w", encoding="utf-8") as f:
            json.dump({"source": self.source, "groupes": data}, f,
                      ensure_ascii=False, indent=2)


if __name__ == "__main__":
    import sys
    xlsx = sys.argv[1] if len(sys.argv) > 1 else "aide_pour_dessinateur.xlsx"
    t = TablePliage.depuis_excel(xlsx)
    print(f"{len(t.groupes)} groupes de matière lus :")
    for nom, g in t.groupes.items():
        eps = sorted(g.valeurs)
        print(f"  - {nom}  ({len(eps)} épaisseurs : {eps})")
