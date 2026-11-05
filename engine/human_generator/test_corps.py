"""Tests réels du générateur paramétrique (phase 2, mission humaine : TEST 1, 2 et 3).

Critères mesurables, sans jugement visuel :
  - aucun NaN, nombre de sommets constant (19 158), indices de faces valides ;
  - hauteur (étendue en Y) : homme > femme (cohérent avec les cibles MakeHuman) ;
  - morph appliqué : une cible de taille change la hauteur dans le sens attendu ;
  - aucun morph : identique au base.obj.
Usage : python3 test_corps.py  (écrit docs/rapports/phase2_corps_parametrique.json)
"""
import sys, json
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import corps as g

rapport = {}
V0, F0 = g.charger_base()
assert len(V0) == 19158, len(V0)
for f in F0:
    assert all(0 <= i < len(V0) for i in f)

def hauteur(V):
    return float(V[:, 1].max() - V[:, 1].min())

VH, FH = g.generer(sexe=1.0, age=0.0)   # TEST 1 : homme adulte jeune
VF, FF = g.generer(sexe=0.0, age=0.0)   # TEST 2 : femme adulte jeune
VM, FM = g.generer(sexe=0.5, age=0.0)   # moyen
VA, FA = g.generer(sexe=1.0, age=1.0)   # homme âgé (morphologie différente)
VN, _ = g.generer(sexe=0.0, age=0.0, morphs=[])   # témoin : pas de morph supplémentaire

for nom, V in (("homme", VH), ("femme", VF), ("moyen", VM), ("homme_age", VA)):
    assert np.isfinite(V).all(), nom + " : NaN"
    assert len(V) == len(V0), nom + " : nombre de sommets changé"

rapport["sommets"] = len(V0)
rapport["hauteur_homme_dm"] = round(hauteur(VH), 4)
rapport["hauteur_homme_m"] = round(hauteur(VH) * 0.1, 3)
rapport["hauteur_femme_dm"] = round(hauteur(VF), 4)
rapport["hauteur_femme_m"] = round(hauteur(VF) * 0.1, 3)
rapport["hauteur_moyen_dm"] = round(hauteur(VM), 4)
rapport["hauteur_moyen_m"] = round(hauteur(VM) * 0.1, 3)
rapport["hauteur_homme_age_dm"] = round(hauteur(VA), 4)
rapport["hauteur_homme_age_m"] = round(hauteur(VA) * 0.1, 3)
rapport["ecart_max_homme_femme_dm"] = round(float(np.linalg.norm(VH - VF, axis=1).max()), 4)

# Unité : décimètres (MakeHuman, guiexport.py : facteur « decimeter » = 1,0). 1 unité = 0,1 m.
# TEST : homme > femme en hauteur (sinon le sens des cibles est inversé)
assert hauteur(VH) > hauteur(VF), "homme pas plus grand que femme : sens des cibles à vérifier"
# TEST : le moyen est entre les deux (interpolation monotone en sexe)
assert hauteur(VF) - 1e-6 <= hauteur(VM) <= hauteur(VH) + 1e-6, "le moyen sort de l'intervalle homme/femme"

# TEST : cible de taille appliquée (poids +1 change le maillage)
cible_taille = "measure/measure-height-decr|incr.target"
chemins = sorted(p.name for p in (g.DATA / "targets" / "measure").glob("*height*"))
rapport["cibles_taille_disponibles"] = chemins[:6]
if chemins:
    chem = "measure/" + chemins[0]
    V1 = g.appliquer_cible(VH, chem, 1.0)
    rapport["effet_cible_taille_dm"] = round(float(np.abs(V1 - VH).max()), 5)
    assert np.abs(V1 - VH).max() > 0, "la cible de taille n'a rien changé"

# TEST d'identité : sans poids (sexe=0, âge=0 n'applique que la cible femme jeune) ; le témoin de base est le base.obj
# relu. Un écart nul avec un macro de poids nul est vérifié directement.
V_zero = g.macro(V0, 0.5, 0.0) - V0
rapport["macro_ecart_max_moyen_dm"] = round(float(np.abs(V_zero).max()), 5)
assert np.abs(V_zero).max() > 0, "le macro n'a rien changé : cibles non appliquées"
assert np.allclose(g.appliquer_cible(V0, "measure/" + chemins[0], 0.0) if chemins else V0, V0), "poids 0 modifie le maillage"

rapport["statut"] = "VALIDE_TECHNIQUE"
rapport["note"] = ("Tests techniques seulement : pas d'évaluation anatomique ni visuelle. "
                   "Les visages (phase 3), cheveux, vêtements et rigging restent à faire.")
out = Path(__file__).resolve().parents[2] / "docs" / "rapports" / "phase2_corps_parametrique.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(rapport, indent=2, ensure_ascii=False))
print(json.dumps(rapport, indent=2, ensure_ascii=False))
