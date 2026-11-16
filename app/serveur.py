"""
Serveur web local — brique 5.

Lancer :  python -m app.serveur     puis ouvrir http://127.0.0.1:5000

Interface (forme A) : glisser un PDF -> vérifier/corriger -> cocher DXF/STEP
-> générer. Tout tourne en local, aucune donnée ne sort du poste.
"""
from __future__ import annotations
import os
import re
import secrets
import sys
import tempfile

from flask import (Flask, render_template, request, jsonify,
                   send_from_directory, abort)

from moteur.table_pliage import TablePliage
from moteur.profil import Profil
from moteur.generation import generer, construire_profil
from moteur.lecture_pdf import lire_cartouche


def _base_dir() -> str:
    """Dossier des ressources embarquées (= _MEIPASS une fois empaqueté en .exe)."""
    if getattr(sys, "frozen", False):
        return sys._MEIPASS  # type: ignore[attr-defined]
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _app_dir() -> str:
    """Dossier de l'application (à côté de l'exe) : données éditables + sorties."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


BASE = _base_dir()
APPDIR = _app_dir()
TEMPLATES = os.path.join(BASE, "app", "templates")
SORTIES = os.path.join(APPDIR, "sorties", "web")
os.makedirs(SORTIES, exist_ok=True)

app = Flask(__name__, template_folder=TEMPLATES)


def _charger_table() -> TablePliage:
    # priorité au dossier data/ à côté de l'exe (où l'atelier dépose son .xlsx),
    # sinon la table figée embarquée.
    for d in (os.path.join(APPDIR, "data"), os.path.join(BASE, "data")):
        if os.path.isdir(d):
            try:
                return TablePliage.charger(d)
            except Exception:
                continue
    raise FileNotFoundError("Table de pliage introuvable (ni .xlsx ni table_pliage.json).")


TABLE = _charger_table()


# ----------------------------------------------------------------- pages
@app.get("/")
def index():
    return render_template("index.html")


# --------------------------------------------------------------- données table
@app.get("/api/materiaux")
def api_materiaux():
    """Structure matière -> épaisseurs -> matrices (pour les menus déroulants)."""
    out = []
    for nom, g in TABLE.groupes.items():
        eps = []
        for ep in sorted(g.valeurs):
            mats = [{"matrice": d["matrice"], "deduction": d["deduction"]}
                    for d in TABLE.matrices_disponibles(nom, ep)]
            if mats:
                eps.append({"epaisseur": ep, "matrices": mats,
                            "defaut": mats[0]["matrice"]})
        if eps:
            out.append({"matiere": nom, "epaisseurs": eps})
    return jsonify(out)


# ------------------------------------------------------------- analyse d'un PDF
@app.post("/api/analyser")
def api_analyser():
    f = request.files.get("pdf")
    if not f:
        return jsonify({"erreur": "Aucun fichier PDF reçu."}), 400
    tmp = os.path.join(tempfile.gettempdir(), secrets.token_hex(6) + ".pdf")
    f.save(tmp)
    try:
        champs = lire_cartouche(tmp)
    except Exception as e:
        return jsonify({"erreur": f"Lecture PDF : {e}"}), 500
    finally:
        try: os.remove(tmp)
        except OSError: pass
    return jsonify(champs)


# ------------------------------------------------------- calcul déplié (direct)
@app.post("/api/deplie")
def api_deplie():
    p = request.get_json(force=True) or {}
    try:
        profil = construire_profil(p)
        return jsonify({"ok": True, "deplie": profil.deplie(TABLE)})
    except Exception as e:
        return jsonify({"ok": False, "erreur": str(e)})


# -------------------------------------------------------------- génération
@app.post("/api/generer")
def api_generer():
    p = request.get_json(force=True) or {}
    token = secrets.token_hex(8)
    dossier = os.path.join(SORTIES, token)
    try:
        res = generer(p, TABLE, dossier)
    except Exception as e:
        return jsonify({"ok": False, "erreur": str(e)}), 400

    def url(path):
        return f"/fichiers/{token}/{os.path.basename(path)}" if path else None

    return jsonify({
        "ok": True,
        "deplie": res.get("deplie"),
        "infos_step": res.get("infos_step"),
        "avertissements": res.get("avertissements", []),
        "fichiers": {k: url(v) for k, v in res["fichiers"].items()},
        "apercus": {k: url(v) for k, v in res["apercus"].items()},
    })


@app.get("/fichiers/<token>/<path:nom>")
def fichiers(token, nom):
    if not re.fullmatch(r"[0-9a-f]{16}", token):
        abort(404)
    dossier = os.path.join(SORTIES, token)
    if not os.path.isdir(dossier):
        abort(404)
    return send_from_directory(dossier, nom, as_attachment=nom.endswith((".dxf", ".step")))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
