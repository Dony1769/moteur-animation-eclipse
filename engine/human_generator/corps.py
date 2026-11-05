"""Générateur de corps humain paramétrique (phase 2), à partir des assets CC0 de MakeHuman.

Source des données : makehumancommunity/makehuman, dossier makehuman/data (LICENSE.ASSETS.md : CC0 1.0 Universal ;
les fichiers 3dobjs/base.obj et targets/*.target portent la mention « released as CC0 in september 2020 »).
Le code MakeHuman (AGPL) n'est PAS utilisé : seules les données CC0 sont lues. Le format (lignes « index dx dy dz » des
fichiers .target, faces « f a/b/c » du base.obj) est décrit dans ces fichiers eux-mêmes.

Méthode :
  - Le maillage de base est le corps neutre (19 158 sommets).
  - Un morph macro est une combinaison pondérée de cibles « universal-{sexe}-{âge}-{muscle}-{poids} » (morphing
    multi-cibles bilinéaire sur sexe et âge, comme dans MakeHuman). Pour l'adulte : sexe ∈ [0,1] (0 femme, 1 homme),
    âge ∈ [0,1] (0 jeune adulte, 1 âge avancé). Muscle et poids restent moyens (phase MVP).
  - Les autres cibles (taille, mesures) sont ajoutées par poids explicites.

Limites connues (à écrire dans docs/) : pas d'ethnicité (cibles race non utilisées), pas de visage détaillé (phase 3),
pas de cheveux ni de vêtements (phases 5), pas de rigging (phase 6).
"""
from pathlib import Path
import numpy as np

DATA = Path("/home/claude/makehumancommunity/makehuman/makehuman/data")


def charger_base():
    """Lit base.obj : sommets (N,3) et faces (F,k) indexées à partir de 0. Les faces peuvent être des quads."""
    V, F = [], []
    for ligne in (DATA / "3dobjs" / "base.obj").read_text().splitlines():
        if ligne.startswith("v "):
            V.append([float(x) for x in ligne.split()[1:4]])
        elif ligne.startswith("f "):
            F.append([int(v.split("/")[0]) - 1 for v in ligne.split()[1:]])
    return np.asarray(V, dtype=float), F


_cache = {}


def charger_cible(nom_chemin):
    """Lit un fichier .target : renvoie (indices, deltas). Les lignes de commentaire (#) sont ignorées."""
    if nom_chemin in _cache:
        return _cache[nom_chemin]
    idx, dx = [], []
    for ligne in (DATA / "targets" / nom_chemin).read_text().splitlines():
        p = ligne.split()
        if len(p) == 4 and not ligne.startswith("#"):
            idx.append(int(p[0])); dx.append([float(p[1]), float(p[2]), float(p[3])])
    _cache[nom_chemin] = (np.asarray(idx, dtype=int), np.asarray(dx, dtype=float))
    return _cache[nom_chemin]


def appliquer_cible(V, nom_chemin, poids):
    if poids == 0.0:
        return V
    idx, d = charger_cible(nom_chemin)
    V = V.copy()
    V[idx] += poids * d
    return V


RACES = ("african", "asian", "caucasian")   # MakeHuman : morphologie moyenne = mélange égal des trois races


def macro(V, sexe, age):
    """Morph macro adulte. sexe : 0 femme, 1 homme. age : 0 jeune adulte, 1 âge avancé.

    Les fichiers « universal-* » du dépôt sont des pointeurs LFS (604 octets) : leur contenu n'est pas disponible via
    le clone anonyme (entrée 133). On utilise donc les cibles par race (african/asian/caucasian × sexe × âge, données
    réelles, même licence CC0), mélangées à poids égaux (1/3 par race), ce que MakeHuman fait pour la morphologie moyenne.
    Le maillage est une somme pondérée des 12 combinaisons (race × sexe × âge), chacune ajoutée au base comme delta.
    """
    if not (0.0 <= sexe <= 1.0 and 0.0 <= age <= 1.0):
        raise ValueError("sexe et âge doivent être dans [0, 1]")
    out = V.copy()
    for r in RACES:
        for g, wg in (("female", 1 - sexe), ("male", sexe)):
            for a, wa in (("young", 1 - age), ("old", age)):
                w = (1.0 / len(RACES)) * wg * wa
                if w == 0.0:
                    continue
                idx, d = charger_cible(f"macrodetails/{r}-{g}-{a}.target")
                out[idx] += w * d
    return out


def generer(sexe=0.5, age=0.0, morphs=None):
    """Retourne (sommets, faces). morphs : liste de (chemin_relatif_cible, poids) appliquée après le macro."""
    V, F = charger_base()
    V = macro(V, sexe, age)
    for chemin, p in (morphs or []):
        V = appliquer_cible(V, chemin, p)
    return V, F


def ecrire_obj(chemin, V, F):
    with open(chemin, "w") as f:
        for v in V:
            f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
        for face in F:
            f.write("f " + " ".join(str(i + 1) for i in face) + "\n")
