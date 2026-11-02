"""Validation des manifests de personnage (format monteur/personnage/1).

Un manifest liste, par catégorie, le fichier image de chaque élément :
- vues : au moins « face » ;
- poses : « marche_1 » à « marche_4 » (cycle de marche) ;
- expressions : « neutre », « joie », « tristesse », « colere », « surprise » ;
- bouche : formes « A », « E », « I », « M », « O », « U ».

Un fichier manquant (ou une forme requise absente) est une erreur.
Usage : python3 engine/personnages/valider.py [dossier_manifests]
"""
import glob
import json
import os
import sys

RACINE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REQUIS = {
    "vues": ["face"],
    "poses": ["marche_1", "marche_2", "marche_3", "marche_4"],
    "expressions": ["neutre", "joie", "tristesse", "colere", "surprise"],
    "bouche": ["A", "E", "I", "M", "O", "U"],
}


def valider(manifest, racine=RACINE):
    """Renvoie la liste des erreurs (vide = personnage valide)."""
    erreurs = []
    if manifest.get("format") != "monteur/personnage/1":
        erreurs.append("format inconnu : %r" % manifest.get("format"))
    for cle in ("id", "nom"):
        if not manifest.get(cle):
            erreurs.append("%s manquant" % cle)
    for categorie, requis in REQUIS.items():
        elements = manifest.get(categorie) or {}
        for nom in requis:
            if nom not in elements:
                erreurs.append("%s : « %s » absent du manifest" % (categorie, nom))
                continue
            chemin = os.path.join(racine, elements[nom])
            if not os.path.isfile(chemin):
                erreurs.append("%s : fichier manquant pour « %s » (%s)" % (categorie, nom, elements[nom]))
    return erreurs


def main():
    dossier = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RACINE, "personnages")
    echec = False
    for chemin in sorted(glob.glob(os.path.join(dossier, "*.json"))):
        with open(chemin, encoding="utf-8") as f:
            manifest = json.load(f)
        erreurs = valider(manifest)
        statut = "OK" if not erreurs else "ÉCHEC (%d erreur(s))" % len(erreurs)
        print("%-20s %s" % (manifest.get("id", os.path.basename(chemin)), statut))
        for e in erreurs:
            print("    -", e)
        echec = echec or bool(erreurs)
    return 1 if echec else 0


if __name__ == "__main__":
    sys.exit(main())
