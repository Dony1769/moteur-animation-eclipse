"""Construit la page du visualiseur HBM : injecte les données (viz.json, sortie de
engine/skinning/exporter_visualiseur.py) dans le gabarit modele.html.
Usage : python3 construire.py viz.json sortie.html
"""
import sys, os
here = os.path.dirname(os.path.abspath(__file__))
donnees = open(sys.argv[1], encoding="utf-8").read()
gabarit = open(os.path.join(here, "modele.html"), encoding="utf-8").read()
assert "__DONNEES__" in gabarit and "</script" not in donnees
open(sys.argv[2], "w", encoding="utf-8").write(gabarit.replace("__DONNEES__", donnees))
print("ECRIT", sys.argv[2])
