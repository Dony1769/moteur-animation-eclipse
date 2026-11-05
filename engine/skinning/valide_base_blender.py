"""Validation dans Blender de la base de poids finale et des correctifs ARAP (phase 4).

Pour chaque chaîne (LeftArm, LeftForeArm, LeftLeg) et angle de test (60, 75, 90, 105, 120) :
 - pose de l'armature (mesure_lbs.poser), poids finaux écrits dans les groupes de sommets ;
 - plis LBS (sans correctif) et plis avec correctif (déplacements de repos), même règle que mesure_lbs ;
 - étirement max des arêtes, avec et sans correctif.
Les correctifs à 75 et 105 sont interpolés entre les clés voisines (60/90 et 90/120), comme en numpy.
Vérifie d'abord que l'ordre des sommets du maillage correspond à donnees7 (sinon arrêt).

Usage : blender -b --factory-startup --disable-autoexec COPIE.blend -P engine/skinning/valide_base_blender.py -- W.npz CORR.npz ORDRE.json REPOS.npz SORTIE.json
"""
import sys, json, numpy as np, bpy
from mathutils import Vector
sys.path.insert(0, "/home/claude/moteur_3_0/engine/skinning")
import mesure_lbs as m

argv = sys.argv[sys.argv.index("--") + 1:]
w_npz, corr_npz, ordre_json, repos_npz, sortie = argv[:5]
corps = max([o for o in bpy.data.objects if o.type == "MESH"], key=lambda o: len(o.data.vertices))
arm = [o for o in bpy.data.objects if o.type == "ARMATURE"][0]
for mod in corps.modifiers:
    if mod.type != "ARMATURE":
        mod.show_viewport = False; mod.show_render = False

# 1. contrôle d'ordre des sommets
R = np.load(repos_npz)["rest"]
cw, aw = corps.matrix_world.copy(), arm.matrix_world.copy()
inv_c, inv_a = cw.inverted(), aw.inverted()
x_arm = np.array([list(inv_a @ (cw @ v.co)) for v in corps.data.vertices])
ecart = float(np.abs(x_arm - R).max())
if ecart > 1e-3:
    raise SystemExit(f"ordre des sommets différent (écart max {ecart:.4g})")
print("ORDRE OK, écart max", ecart)

# 2. poids finaux
W = np.load(w_npz)["W"]; W = W / W.sum(1, keepdims=True)
ordre = json.load(open(ordre_json))
for g in list(corps.vertex_groups):
    corps.vertex_groups.remove(g)
groupes = [corps.vertex_groups.new(name=n) for n in ordre]
for i, v in enumerate(corps.data.vertices):
    for b in np.nonzero(W[i] > 1e-9)[0]:
        groupes[b].add([i], float(W[i, b]), "REPLACE")
print("POIDS ECRITS", len(corps.data.vertices))

# 3. correctifs de repos -> déplacements locaux
C = np.load(corr_npz)
def dec_local(d):
    out = []
    for i, v in enumerate(corps.data.vertices):
        cible = inv_c @ (aw @ Vector(x_arm[i] + d[i]))
        out.append(cible - v.co)
    return out

CH = [("LeftArm", "mixamorig:LeftArm", (0, 1, 0)), ("LeftForeArm", "mixamorig:LeftForeArm", (0, 1, 0)),
      ("LeftLeg", "mixamorig:LeftLeg", (1, 0, 0))]
def corr_pour(chaine, a):
    if a in (60, 90, 120):
        return C[f"{chaine}_{a}"]
    lo, hi = (60, 90) if a < 90 else (90, 120)
    t = (a - lo) / (hi - lo)
    return (1 - t) * C[f"{chaine}_{lo}"] + t * C[f"{chaine}_{hi}"]

def etirement_max(rest_, pose_):
    e = corps.data.edges
    ratios = []
    for ed in e:
        a_, b_ = ed.vertices
        r0 = (rest_[b_] - rest_[a_]).length
        if r0 < 1e-9: continue
        ratios.append(((pose_[b_] - pose_[a_]).length) / r0)
    return max(ratios)

def plis_definition(rest_ref, pose, dom, mats):
    """Même règle que mesure_lbs.faces_repliees, mais la normale de repos est celle du maillage ORIGINAL
    (sans correctif) : la règle des plis ne change pas quand on ajoute un correctif (erreur 75)."""
    n = 0
    for p_ in corps.data.polygons:
        boucle = list(p_.vertices)
        nr = m.normale_newell(rest_ref, boucle); npz = m.normale_newell(pose, boucle)
        votes = {}
        for i in boucle:
            if dom[i]:
                votes[dom[i]] = votes.get(dom[i], 0) + 1
        if not votes or nr.length == 0 or npz.length == 0:
            continue
        os_nom = max(votes, key=votes.get)
        Rm = mats[os_nom].to_3x3().normalized()
        if npz.dot(Rm @ nr) < 0:
            n += 1
    return n

resultats = {}
for nom_chaine, nom_os, axe in CH:
    for a in (60, 75, 90, 105, 120):
        repos_pose = m.poser(arm, nom_os, axe, a)
        mats = m.matrices(arm)
        rest0, pose0, dom0 = m.positions_lbs(corps, arm, mats)
        n_lbs = plis_definition(rest0, pose0, dom0, mats)
        et_lbs = etirement_max(rest0, pose0)
        dec = dec_local(corr_pour(nom_chaine, a))
        rest1, pose1, dom1 = m.positions_lbs(corps, arm, mats, decalage=dec)
        n_cor = plis_definition(rest0, pose1, dom1, mats)
        et_cor = etirement_max(rest0, pose1)
        resultats[f"{nom_chaine}@{a}"] = {"plis_lbs": n_lbs, "plis_corr": n_cor,
                                           "etirement_lbs": round(et_lbs, 3), "etirement_corr": round(et_cor, 3)}
        print("RES", nom_chaine, a, resultats[f"{nom_chaine}@{a}"], flush=True)
        arm.pose.bones[nom_os].matrix = repos_pose
        bpy.context.view_layer.update()
json.dump(resultats, open(sortie, "w"), indent=2)
print("VALIDE_OK", sortie)
