"""Fusion de vues sur les faces d'un maillage (texturage sans modèle entraîné).

Idée lue dans la méthode de texturage multi-vues de Hunyuan3D-Paint (documentation DeepWiki, rapport arXiv 2506.15442
section 3.2) : chaque vue contribue à une face selon (1) le cosinus entre la normale de la face et la direction de la
vue, élevé à la puissance bake_exp = 4 ; (2) un poids propre à la vue (face avant 1,0, arrière 0,5, côtés 0,1, dessus et
dessous 0,05). La couleur finale est la moyenne pondérée. Les faces qu'aucune vue ne voit reçoivent un remplissage.

Réimplémentation maison : aucun code ni poids de Tencent n'est utilisé.

Limites explicites (non traitées ici) : pas de test de visibilité (occlusion) : une vue peut « voir » une face cachée
derrière le corps ; cela sera à ajouter avant tout usage sur un personnage réel.
"""
import numpy as np

BAKE_EXP = 4.0
POIDS_VUE = {"avant": 1.0, "arriere": 0.5, "gauche": 0.1, "droite": 0.1, "dessus": 0.05, "dessous": 0.05}
VUES_CANONIQUES = {          # direction du vers la caméra (unitaire)
    "avant": np.array([0.0, 0.0, 1.0]), "arriere": np.array([0.0, 0.0, -1.0]),
    "droite": np.array([1.0, 0.0, 0.0]), "gauche": np.array([-1.0, 0.0, 0.0]),
    "dessus": np.array([0.0, 1.0, 0.0]), "dessous": np.array([0.0, -1.0, 0.0]),
}


def normales_faces(V, F):
    e1 = V[F[:, 1]] - V[F[:, 0]]
    e2 = V[F[:, 2]] - V[F[:, 0]]
    n = np.cross(e1, e2)
    return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)


def fusionner(V, F, couleurs_par_vue, poids_vue=None, bake_exp=BAKE_EXP):
    """couleurs_par_vue : dict nom_vue -> (F, 3) couleur de chaque face vue par cette vue.
    Retourne (couleurs (F,3), couverture (F,) poids total).

    Une face reçoit de la vue v le poids w = max(0, n·c_v)^bake_exp × poids_vue[v]. Une face avec un poids total nul
    n'est pas remplie (elle reste à 0 et est comptée dans les faces non couvertes).
    """
    poids_vue = poids_vue or POIDS_VUE
    N = normales_faces(V, F)
    num = np.zeros((len(F), 3))
    den = np.zeros(len(F))
    for nom, couleur in couleurs_par_vue.items():
        c = VUES_CANONIQUES[nom]
        cosinus = np.clip(N @ c, 0.0, None)
        w = (cosinus ** bake_exp) * poids_vue[nom]
        num += w[:, None] * couleur
        den += w
    couv = den
    out = np.zeros((len(F), 3))
    ok = den > 1e-12
    out[ok] = num[ok] / den[ok][:, None]
    return out, couv
