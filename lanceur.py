"""
Point d'entrée de l'application autonome (.exe).

Démarre le serveur local et ouvre le navigateur sur l'interface.
"""
import os
os.environ.setdefault("MPLBACKEND", "Agg")

import threading
import time
import webbrowser

URL = "http://127.0.0.1:5000"


def _ouvrir_navigateur():
    time.sleep(1.8)
    try:
        webbrowser.open(URL)
    except Exception:
        pass


def main():
    print("=" * 56)
    print("  TOLERIE FACADE  -  PDF vers DXF / STEP")
    print("=" * 56)
    print(f"\n  Application demarree : {URL}")
    print("  (Laisse cette fenetre ouverte pendant le travail.)")
    print("  Pour quitter : ferme la fenetre.\n")
    threading.Thread(target=_ouvrir_navigateur, daemon=True).start()
    from app.serveur import app
    app.run(host="127.0.0.1", port=5000, debug=False)


if __name__ == "__main__":
    main()
