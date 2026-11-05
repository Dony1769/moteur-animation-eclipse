"""Classification des faces extérieures d'un maillage (règle de Takayama et al. 2014, réimplémentée).

Source officielle : Takayama, Sugihara, Igarashi (2014), « A Simple Method for Correcting Facet Orientations in Polygon
Meshes Based on Ray Casting », Journal of Computer Graphics Techniques 3(4), page projet
https://users.cs.utah.edu/~ladislav/takayama14simple/takayama14simple.html (PDF lu le 5 novembre 2026).
Règle retenue : pour chaque face, on lance des rayons depuis des points tirés sur la face, dans des directions aléatoires,
des deux côtés. cfront = rayons non bloqués partant du côté de la normale ; cback = même chose de l'autre côté.
Une face est EXTÉRIEURE si au moins un côté voit de l'espace libre (cfront + cback > 0) ; sinon elle est INTÉRIEURE.
Le côté extérieur est celui qui voit le plus de rayons libres (cfront < cback : la face doit être retournée).

Lancer de rayon : trimesh (BVH rtree), réimplémentation de la règle ; aucun code de Takayama n'est copié.
"""
import numpy as np
import trimesh

LOT_RAYONS = 256   # taille de lot : borne la mémoire du lancer de rayon sans embree


def classer(V, F, points_par_face=2, directions=32, seed=0):
    """Retourne (exterieure (F,) bool, cfront (F,), cback (F,), a_retourner (F,) bool).

    Les faces dégénérées (aire nulle, normale indéfinie) sont marquées intérieures et comptées à part : la règle ne
    s'applique pas à elles (entrée 140).
    """
    rng = np.random.default_rng(seed)
    m = trimesh.Trimesh(vertices=V, faces=F, process=False)
    aire = 0.5 * np.linalg.norm(np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]), axis=1)
    degeneree = aire < 1e-12
    N = m.face_normals
    nf = len(F)
    # points aléatoires sur chaque face (coordonnées barycentriques uniformes)
    r1 = rng.random((nf, points_par_face)); r2 = rng.random((nf, points_par_face))
    s = np.sqrt(r1)
    b0 = 1 - s; b1 = s * (1 - r2); b2 = s * r2
    tri = V[F]                                      # (F,3,3)
    pts = b0[..., None] * tri[:, None, 0] + b1[..., None] * tri[:, None, 1] + b2[..., None] * tri[:, None, 2]
    pts = pts.reshape(-1, 3)
    face_id = np.repeat(np.arange(nf), points_par_face)
    # directions uniformes sur la sphère
    d = rng.normal(size=(directions, 3)); d /= np.linalg.norm(d, axis=1, keepdims=True)
    cfront = np.zeros(nf, dtype=int); cback = np.zeros(nf, dtype=int)
    eps = 1e-4
    for dk in d:
        cote = np.sign(N[face_id] @ dk)              # +1 : côté normale ; -1 : autre côté
        ok = cote != 0
        origine = pts + eps * dk * np.sign(np.where(ok, cote, 1))[:, None]   # décalage du côté du rayon
        # Lots de rayons : sans embree, trimesh construit une matrice rayons x triangles en mémoire
        # (≈ 37 000 x 18 000 pour le corps) et le processus est tué (entrée 140, mesure du 5 novembre).
        bloque = np.zeros(len(origine), dtype=bool)
        for k in range(0, len(origine), LOT_RAYONS):
            o = origine[k:k + LOT_RAYONS]
            bloque[k:k + len(o)] = m.ray.intersects_any(o, np.tile(dk, (len(o), 1)))
        libre = ok & (~bloque)
        np.add.at(cfront, face_id[libre & (cote > 0)], 1)
        np.add.at(cback, face_id[libre & (cote < 0)], 1)
    exterieure = ((cfront + cback) > 0) & (~degeneree)
    a_retourner = exterieure & (cfront < cback)
    return exterieure, cfront, cback, a_retourner
