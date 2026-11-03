"""Contrôle de gonflement / effondrement d'une déformation skinnée (mesure réelle, sans supposition).

Deux indicateurs calculés sur le maillage ÉVALUÉ par Blender (modificateur Armature actif),
pour chaque angle et chaque mode (LBS = use_deform_preserve_volume False, DQS = True) :

1. ratio_volume : volume signé du maillage fermé / volume de repos. 1.0 = volume conservé.
   Un effondrement (« papier froissé », pincement) fait baisser le ratio ; un gonflement le fait monter.
2. etirement_max : max(longueur_pose / longueur_repos) sur toutes les arêtes.
   etirement_min : min du même ratio. Un ratio < 1 signale une arête compressée (pli, pincement).
3. ecart_p99 : 99e centile de |ratio - 1| sur les arêtes ; mesure la part de l'arête déformée.

Limites (à garder en tête) :
- Le volume est une grandeur globale : il peut rester stable malgré un pincement local. Les arêtes
  et le nombre de replis (mesure_lbs.faces_repliees) servent donc de contrôle local complémentaire.
- Le maillage doit être fermé pour que le volume ait un sens ; le corps HBM l'est (les yeux sont des objets à part).
- Témoin : à 0 degré, ratio_volume = 1 et étirements = 1 (vérifié dans le rapport).

Usage : blender -b corps_final.blend -P engine/skinning/controle_gonflement.py -- SORTIE.json
"""
import bpy, sys, json
sys.path.insert(0, "/home/claude/moteur_3_0/engine/skinning")
import auto_skin as ak
import pose_chaine as pc

ANGLES = (0, 60, 90, 105, 120)
# os testés : (nom, axe monde de flexion, préfixe des clés correctives)
ARTICULATIONS = [("mixamorig:LeftArm", (0, 1, 0)), ("mixamorig:LeftForeArm", (0, 1, 0)),
                 ("mixamorig:LeftLeg", (1, 0, 0))]


def volume_signe(coords, polygones):
    """Volume signé (somme des tétraèdres de chaque face triangulée en éventail)."""
    v = 0.0
    for poly in polygones:
        a = coords[poly[0]]
        for k in range(1, len(poly) - 1):
            b = coords[poly[k]]; c = coords[poly[k + 1]]
            v += a.dot(b.cross(c)) / 6.0
    return v


def ecarts_aretes(coords, rest, aretes):
    """Ratios longueur pose / longueur repos sur toutes les arêtes."""
    out = []
    for i, j in aretes:
        lr = (rest[i] - rest[j]).length
        if lr > 0:
            out.append((coords[i] - coords[j]).length / lr)
    return out


def centile(valeurs, p):
    s = sorted(valeurs)
    return s[min(len(s) - 1, int(round(p * (len(s) - 1))))]


argv = sys.argv[sys.argv.index("--") + 1:]
sortie = argv[0]
# variante « sans » : clés correctives désactivées (témoin de l'effet des clés)
AVEC_CLES = not (len(argv) > 1 and argv[1] == "sans")
# fichier .blend à mesurer (par défaut : pipeline final non lissé)
BLEND = argv[2] if len(argv) > 2 else "/tmp/claude-0/-home-claude/9ce8e1e5-f7cf-5619-8a75-3c6d9a11ab1c/scratchpad/corps_final.blend"

bpy.ops.wm.open_mainfile(filepath=BLEND)
corps = bpy.data.objects[ak.ENTREE_NOM]
arm = [m.object for m in corps.modifiers if m.type == "ARMATURE"][0]
am = [m for m in corps.modifiers if m.type == "ARMATURE"][0]
corps.modifiers["Multires"].show_viewport = False
kb = corps.data.shape_keys.key_blocks
base = kb["Basis"].data

# repos de référence : forme de base, toutes clés à 0
for k in kb:
    k.value = 0.0
bpy.context.view_layer.update()
rest_local = [v.co.copy() for v in corps.data.vertices]
polys = [list(p.vertices) for p in corps.data.polygons]
aretes = [tuple(e.vertices) for e in corps.data.edges]
vol_repos = volume_signe(rest_local, polys)


def evalue():
    """Coordonnées locales du maillage évalué par Blender (même topologie, Multires désactivé)."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = corps.evaluated_get(dg)
    m = ev.to_mesh()
    coords = [v.co.copy() for v in m.vertices]
    ev.to_mesh_clear()
    return coords


def valeurs_cles(nom, a):
    if not AVEC_CLES:
        return
    c1 = "corr_" + nom.replace("mixamorig:", "")
    c2 = "c120_" + nom.replace("mixamorig:", "")
    kb[c1].value = min(a / 90, 1.0)
    kb[c2].value = max(0.0, min((a - 90) / 30, 1.0))
    bpy.context.view_layer.update()


def reset_cles():
    for k in kb:
        k.value = 0.0
    bpy.context.view_layer.update()


res = {"variante": "avec_cles" if AVEC_CLES else "sans_cles", "angles": list(ANGLES), "modes": {}, "volume_repos": round(vol_repos, 6)}
for mode in ("LBS", "DQS"):
    am.use_deform_preserve_volume = (mode == "DQS")
    res["modes"][mode] = {}
    for nom, axe in ARTICULATIONS:
        par = {}
        for a in ANGLES:
            reset_cles()
            valeurs_cles(nom, a)
            sauve = pc.poser_chaine(arm, [(nom, axe, a)])
            coords = evalue()
            pc.restaurer(arm, sauve)
            reset_cles()
            ratios = ecarts_aretes(coords, rest_local, aretes)
            par[a] = {
                "ratio_volume": round(volume_signe(coords, polys) / vol_repos, 4),
                "etirement_max": round(max(ratios), 4),
                "etirement_min": round(min(ratios), 4),
                "ecart_p99": round(centile([abs(r - 1.0) for r in ratios], 0.99), 4),
            }
        res["modes"][mode][nom.replace("mixamorig:", "")] = par

json.dump(res, open(sortie, "w"), indent=2)
print("RES", json.dumps(res))
