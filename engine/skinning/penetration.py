"""Mesure de pénétration (phase 4, erreur 86) : un membre ne doit jamais passer à l'intérieur
du reste du corps.

Principe (proxy, pas un test de volume exact, car le maillage n'est pas fermé par segment) :
- « membre » = sommets dont le tendon de jonction suit le sous-arbre articulé (ensemble `mobile`) ;
- « corps » = tous les autres sommets, posés (positions P) ;
- pour chaque sommet mobile v : on prend la face du corps la plus proche (centre c, normale n) ;
- profondeur signée = (v − c) · n. Négative = v est derrière la surface, donc à l'intérieur ;
- pénétration = profondeur < −TOL, pour un sommet dont la distance au repos à p dépasse
  DIST_CONTINUITE (sinon c'est la peau voisine d'une même zone, pas une traversée).

Limites : pas de test de volume fermé ; les membres collés au tronc au repos (aisselle, aine)
sont exclus par DIST_CONTINUITE ; à valider sur des cas connus avant de faire confiance au chiffre.
"""
import numpy as np
from scipy.spatial import cKDTree

TOL = 0.005                 # 5 mm de tolérance de surface
DIST_CONTINUITE = 0.06      # au repos, en dessous de 6 cm : même zone de peau, ignoré


def normales_sommets(P, faces, n):
    """Normales sommets (moyenne des normales de faces), orientées par le repos."""
    N = np.zeros((n, 3))
    for f in faces:
        f = list(f)
        if len(f) < 3:
            continue
        a, b, c = P[f[0]], P[f[1]], P[f[2]]
        nf = np.cross(b - a, c - a)
        for k in f:
            N[k] += nf
    L = np.linalg.norm(N, axis=1, keepdims=True)
    return N / np.maximum(L, 1e-12)


def orienter_faces(faces, rest):
    """Oriente les faces de façon cohérente (chaque arête partagée est parcourue en sens inverse),
    puis choisit le sens global pour que la normale pointe vers l'extérieur au repos.
    Renvoie une liste de faces orientées (mêmes sommets, ordre possiblement inversé)."""
    from collections import defaultdict, deque
    faces = [list(f) for f in faces]
    aretes = defaultdict(list)
    for i, f in enumerate(faces):
        for k in range(len(f)):
            a, b = f[k], f[(k + 1) % len(f)]
            aretes[(min(a, b), max(a, b))].append(i)
    flip = [None] * len(faces)
    for depart in range(len(faces)):
        if flip[depart] is not None:
            continue
        flip[depart] = False
        file = deque([depart])
        while file:
            i = file.popleft()
            f = faces[i] if not flip[i] else faces[i][::-1]
            for k in range(len(f)):
                a, b = f[k], f[(k + 1) % len(f)]
                for j in aretes[(min(a, b), max(a, b))]:
                    if j == i or flip[j] is not None:
                        continue
                    # même sens que f sur l'arête partagée => j doit être inversé
                    g = faces[j]
                    sens = any(g[m] == a and g[(m + 1) % len(g)] == b for m in range(len(g)))
                    flip[j] = sens if not flip[i] else (not sens)
                    file.append(j)
    out = [faces[i][::-1] if flip[i] else faces[i] for i in range(len(faces))]
    # sens global : majorité des normales au repos pointant hors du centre du corps
    N = normales_sommets(rest, out, len(rest))
    c = rest.mean(0)
    if np.einsum("ij,ij->i", N, rest - c).mean() < 0:
        out = [f[::-1] for f in out]
    return out


def profondeur_penetration(rest, P, faces, mobile, centre=None, rayon_zone=0.13, ignorer=None, dom=None):
    """Renvoie (nombre de sommets mobiles en pénétration, profondeur minimale en m, masque).
    rest, P : (n,3) ; faces : liste de listes (maillage fermé et cohérent) ; mobile : masque (n,).
    centre, rayon_zone : zone de jonction exclue (au repos, le maillage se chevauche au pli de l'articulation :
    ce chevauchement est un défaut du repos, pas une pénétration de la pose ; erreur 86).
    Candidats : faces du reste du corps (toutes leurs sommets non mobiles). Pour chaque sommet mobile,
    la face candidate la plus proche (centre de face) donne le signe : profondeur = (v - c) . n_face.
    Sur un maillage fermé, un point situé derrière la face la plus proche est à l'intérieur du volume."""
    n = len(rest)
    corps = ~mobile
    cand = [f for f in faces if all(corps[k] for k in f)]
    if ignorer is not None and dom is not None:
        # os adjacents de la même chaîne : leur chevauchement est une question de jonction (erreur 86)
        cand = [f for f in cand if dom[f[0]] not in ignorer]
    if not cand:
        return 0, 0.0, np.zeros(n, bool)
    C = np.zeros((len(cand), 3)); Nf = np.zeros((len(cand), 3))
    for i, f in enumerate(cand):
        pts = P[list(f)]
        C[i] = pts.mean(0)
        nf = np.cross(pts[1] - pts[0], pts[2] - pts[0])
        Nf[i] = nf / max(np.linalg.norm(nf), 1e-12)
    # centre de face de référence au repos : la distance au repos sert à exclure la peau voisine
    Cr = np.zeros((len(cand), 3))
    for i, f in enumerate(cand):
        Cr[i] = rest[list(f)].mean(0)
    tree = cKDTree(C)
    mob_idx = np.where(mobile)[0]
    d_pose, j = tree.query(P[mob_idx])
    prof = np.einsum("ij,ij->i", P[mob_idx] - C[j], Nf[j])
    d_rest = np.linalg.norm(rest[mob_idx] - Cr[j], axis=1)
    pen = (prof < -TOL) & (d_rest > DIST_CONTINUITE)
    if centre is not None:
        hors_zone = np.linalg.norm(rest[mob_idx] - centre, axis=1) > rayon_zone
        pen &= hors_zone
    masque = np.zeros(n, bool)
    masque[mob_idx[pen]] = True
    return int(pen.sum()), float(prof.min()), masque


def penetration_nouvelle(rest, P, faces, mobile, centre=None, rayon_zone=0.13, dom=None):
    """Pénétrations apparues par rapport au repos.
    Le repos lui-même peut contenir des chevauchements (maillage source) : on ne compte que les
    sommets qui pénètrent dans la pose mais pas au repos. Renvoie (nombre, profondeur min, masque)."""
    n_rep, _, m_rep = profondeur_penetration(rest, rest, faces, mobile, centre, rayon_zone, dom=dom)
    n_pose, pm, m_pose = profondeur_penetration(rest, P, faces, mobile, centre, rayon_zone, dom=dom)
    nouv = m_pose & ~m_rep
    return int(nouv.sum()), pm, nouv
