# Tôlerie Façade — générateur de pièces (PDF → DXF / STEP)

Outil d'aide au dessin pour pièces de façade à section constante
(couvertines, tablettes, bavettes, cornières, profils Z/U…).

À partir d'un plan PDF client (vectoriel), l'outil aide à produire :
- le **DXF de découpe** (flan déplié, lignes de pli, trous/oblongs/découpes) ;
- le **STEP 3D** (profil plié extrudé sur la longueur) — optionnel.

Les **pertes au pli** sont calculées d'après la table maison
(`aide_pour_dessinateur.xlsx`, feuille « tableau facteur K et déduction »),
extraite en `data/table_pliage.json`.

## Structure

```
moteur/        logique métier (table de pliage, dépliage, DXF, STEP, génération)
app/           application web locale (Flask) — forme A
data/          table de pliage (JSON). L'Excel brut N'EST PAS versionné.
```

## Installation (PC d'atelier)

```bash
git clone https://github.com/ganijuamir03-bit/tolerie-facade.git
cd tolerie-facade
pip install -r requirements.txt
# déposer le fichier maison aide_pour_dessinateur.xlsx dans data/ (non versionné)
python -m app.serveur
# puis ouvrir http://127.0.0.1:5000
```

Sans l'Excel dans `data/`, l'appli utilise la table figée `data/table_pliage.json`.

## ⚠️ Sécurité / confidentialité

Ne **jamais** committer :
- `aide_pour_dessinateur.xlsx` — contient des identifiants/mots de passe
  fournisseurs et clients en clair (feuille « Compte client et fournisseur ») ;
- les PDF clients — propriété des clients.

Ces fichiers sont exclus par `.gitignore`. Le dépôt doit rester **privé**.

## Avancement

- [x] 1. Moteur de pliage (lecture table + déduction + dépliage) — testé
- [x] 3. Générateur DXF (contour + plis + trous + découpes) — testé
- [x] 4. Générateur STEP (extrusion du profil plié, rayons de pli) — testé
- [x] 5. Application web locale (formulaire, aperçus, génération) — testé
- [~] 2. Lecture PDF (cartouche OK ; géométrie de coupe + perçages à faire)
- [ ] 6. Pont SolidWorks (optionnel, sur PC Windows)
