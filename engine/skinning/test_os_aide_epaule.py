"""Test d'un os d'aide à l'épaule (torsion/répartition de la rotation du bras).

Idée (combinaison des méthodes lues : « distribuer la rotation sur des os de torsion »,
et du mécanisme Copy Rotation de Blender) :
- un os d'aide, rattaché à Spine1, placé exactement comme le bras (même repos) ;
- une contrainte Copy Rotation le fait suivre `LeftArm` avec une influence de 0,5 ;
- les poids sont recalculés (chaleur) avec cet os présent : il reçoit la zone de transition ;
- mesure des replis (LBS explicite) pour le bras seul, à 60, 90, 105 et 120 degrés.

Variante « sans » : même pipeline, sans l'os d'aide (témoin).
Usage : blender -b corps_hbm.blend -P engine/skinning/test_os_aide_epaule.py -- sans|avec SORTIE.json
"""
import bpy, sys, json
sys.path.insert(0, "/home/claude/moteur_3_0/engine/skinning")
import auto_skin as ak
import mesure_lbs as ml
import pose_chaine as pc

argv = sys.argv[sys.argv.index("--") + 1:]
variante, sortie = argv[0], argv[1]
INFLUENCE = 0.5
AIDE = "mixamorig:LeftArmHelper"

bpy.ops.wm.open_mainfile(filepath="/tmp/claude-0/-home-claude/9ce8e1e5-f7cf-5619-8a75-3c6d9a11ab1c/scratchpad/corps_hbm.blend")
corps = bpy.data.objects[ak.ENTREE_NOM]
pts, m = ak.mesurer(corps)
os_ = ak.definir_squelette(pts, m)
if variante == "avec":
    t, q, _ = os_["mixamorig:LeftArm"]
    os_[AIDE] = (t.copy(), q.copy(), "mixamorig:Spine1")
arm = ak.construire_armature(os_)
ak.skinner(corps, arm)
ak.rattacher_pieces_rigides(arm)
corps.modifiers["Multires"].show_viewport = False

if variante == "avec":
    pb = arm.pose.bones[AIDE]
    c = pb.constraints.new("COPY_ROTATION")
    c.target = arm
    c.subtarget = "mixamorig:LeftArm"
    c.target_space = "WORLD"
    c.owner_space = "WORLD"
    c.influence = INFLUENCE
    bpy.context.view_layer.update()

poids_aide = None
if variante == "avec":
    noms = {g.index: g.name for g in corps.vertex_groups}
    g_aide = corps.vertex_groups.get(AIDE)
    poids_aide = [] if g_aide is None else [g.weight for v in corps.data.vertices for g in v.groups if g.group == g_aide.index]

res = {"variante": variante, "replis_lbs": {}}
for a in (60, 90, 105, 120):
    sauve = pc.poser_chaine(arm, [("mixamorig:LeftArm", (0, 1, 0), a)])
    res["replis_lbs"][a] = ml.faces_repliees(corps, arm, ml.matrices(arm))[0]
    pc.restaurer(arm, sauve)
res["poids_os_aide"] = {"sommets_avec_poids": len(poids_aide) if poids_aide is not None else 0,
                        "poids_max": round(max(poids_aide), 3) if poids_aide else 0.0}
res["audit"] = ak.auditer_poids(corps)
json.dump(res, open(sortie, "w"), indent=2)
print("RES", json.dumps(res))
