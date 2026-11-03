"""Déformation linéaire explicite (LBS) et mesure de repli des faces, sur le maillage de BASE.

- Position skinnée : x' = somme_b w_b * M_b * x, avec M_b = (pose de l'os) * (repos de l'os)^-1, en espace monde.
- Repli : une face est repliée si sa normale skinnée est opposée à la normale de repos tournée par son os dominant.
- Témoin : à 0 degré, aucune face n'est repliée ; LBS doit reproduire le modificateur Blender (écart mesuré).
"""
import bpy, math
from collections import defaultdict
from mathutils import Matrix, Vector

def matrices(arm):
    """Matrice M_b (monde) pour chaque os : pose * repos^-1."""
    res = {}
    for pb in arm.pose.bones:
        rest = arm.matrix_world @ pb.bone.matrix_local
        res[pb.name] = (arm.matrix_world @ pb.matrix) @ rest.inverted()
    return res

def positions_repos(corps, decalage=None):
    """Positions monde de repos ; `decalage` (liste de Vector en espace local) s'ajoute avant skinning."""
    if decalage is None:
        return [corps.matrix_world @ v.co for v in corps.data.vertices]
    return [corps.matrix_world @ (v.co + d) for v, d in zip(corps.data.vertices, decalage)]

def positions_lbs(corps, arm, mats, decalage=None):
    """Positions monde des sommets de base après LBS, et poids dominants (nom d'os) par sommet."""
    noms = {g.index: g.name for g in corps.vertex_groups}
    rest = positions_repos(corps, decalage)
    out, dom = [], []
    for v, x in zip(corps.data.vertices, rest):
        acc = Vector((0.0, 0.0, 0.0)); total = 0.0; meilleur = (0.0, None)
        for g in v.groups:
            nom = noms[g.group]
            if nom not in mats:
                continue
            acc += (mats[nom] @ x) * g.weight; total += g.weight
            if g.weight > meilleur[0]:
                meilleur = (g.weight, nom)
        out.append(acc / total if total > 0 else x)
        dom.append(meilleur[1])
    return rest, out, dom

def normale_newell(coords, boucle):
    n = Vector((0.0, 0.0, 0.0))
    for k in range(len(boucle)):
        a = coords[boucle[k]]; b = coords[boucle[(k + 1) % len(boucle)]]
        n.x += (a.y - b.y) * (a.z + b.z); n.y += (a.z - b.z) * (a.x + b.x); n.z += (a.x - b.x) * (a.y + b.y)
    return n.normalized() if n.length > 0 else n

def faces_repliees(corps, arm, mats, decalage=None, detail=False):
    rest, pose, dom = positions_lbs(corps, arm, mats, decalage)
    n_repliees = 0; compte = defaultdict(int); boucle_repliees = []
    for p in corps.data.polygons:
        boucle = list(p.vertices)
        nr = normale_newell(rest, boucle); npz = normale_newell(pose, boucle)
        # os dominant de la face : vote des sommets
        votes = defaultdict(int)
        for i in boucle:
            if dom[i]:
                votes[dom[i]] += 1
        if not votes or nr.length == 0 or npz.length == 0:
            continue
        os_nom = max(votes, key=votes.get)
        R = mats[os_nom].to_3x3().normalized()
        if npz.dot(R @ nr) < 0:
            n_repliees += 1
            compte[os_nom] += 1
            if detail:
                boucle_repliees.extend(boucle)
    if detail:
        return n_repliees, dict(compte), sorted(set(boucle_repliees))
    return n_repliees, dict(compte)

def ecart_blender(corps, arm, mats):
    """Compare LBS explicite au modificateur Blender (écart maximal, en m) sur les sommets de base."""
    rest, pose, _ = positions_lbs(corps, arm, mats)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = corps.evaluated_get(dg)
    m = ev.to_mesh()
    ecart = 0.0
    for i in range(len(corps.data.vertices)):
        ecart = max(ecart, (corps.matrix_world.inverted() @ pose[i] - m.vertices[i].co).length)
    ev.to_mesh_clear()
    return ecart

def poser(arm, nom, axe, ang):
    pb = arm.pose.bones[nom]
    t = arm.matrix_world @ pb.bone.head_local
    repos = pb.matrix.copy()
    pb.matrix = (Matrix.Translation(t) @ Matrix.Rotation(math.radians(ang), 4, Vector(axe)) @ Matrix.Translation(-t)) @ repos
    bpy.context.view_layer.update()
    return repos

def mesurer_angles(corps, arm, articulations, angles=(0, 30, 60, 90, 120)):
    res = {}
    for nom, axe in articulations:
        par = {}
        for a in angles:
            repos = poser(arm, nom, axe, a)
            n, _ = faces_repliees(corps, arm, matrices(arm))
            par[a] = n
            arm.pose.bones[nom].matrix = repos
            bpy.context.view_layer.update()
        res[nom] = par
    return res
