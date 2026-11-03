"""Répartition de la rotation de l'épaule sur une chaîne de deux os d'aide (sans clés correctives).

Variantes :
- un   : un seul os d'aide à influence 0,5 (référence, identique à test_os_aide_epaule.py « avec »)
- deux : deux os d'aide à influence 0,33 et 0,67 (répartition plus fine de la transition)
Mesures : replis (LBS explicite) et étirement maximal des arêtes (évalué par Blender), à 60/90/105/120 degrés.
Usage : blender -b corps_hbm.blend -P engine/skinning/test_chaine_aide.py -- un|deux SORTIE.json
"""
import bpy, sys, json
sys.path.insert(0, "/home/claude/moteur_3_0/engine/skinning")
import auto_skin as ak
import mesure_lbs as ml
import pose_chaine as pc

argv = sys.argv[sys.argv.index("--") + 1:]
variante, sortie = argv[0], argv[1]
AIDES = {"un": [("mixamorig:LeftArmHelper", 0.5)],
         "deux": [("mixamorig:LeftArmHelper", 0.33), ("mixamorig:LeftArmHelper2", 0.67)]}[variante]

bpy.ops.wm.open_mainfile(filepath="/tmp/claude-0/-home-claude/9ce8e1e5-f7cf-5619-8a75-3c6d9a11ab1c/scratchpad/corps_hbm.blend")
corps = bpy.data.objects[ak.ENTREE_NOM]
pts, m = ak.mesurer(corps)
os_ = ak.definir_squelette(pts, m)
t, q, _ = os_["mixamorig:LeftArm"]
for nom, _infl in AIDES:
    os_[nom] = (t.copy(), q.copy(), "mixamorig:Spine1")
arm = ak.construire_armature(os_)
ak.skinner(corps, arm)
ak.rattacher_pieces_rigides(arm)
corps.modifiers["Multires"].show_viewport = False
for nom, infl in AIDES:
    c = arm.pose.bones[nom].constraints.new("COPY_ROTATION")
    c.target = arm; c.subtarget = "mixamorig:LeftArm"
    c.target_space = "WORLD"; c.owner_space = "WORLD"; c.influence = infl
bpy.context.view_layer.update()

res = {"variante": variante, "aides": AIDES, "replis": {}}
for a in (60, 90, 105, 120):
    sauve = pc.poser_chaine(arm, [("mixamorig:LeftArm", (0, 1, 0), a)])
    res["replis"][a] = ml.faces_repliees(corps, arm, ml.matrices(arm))[0]
    pc.restaurer(arm, sauve)
json.dump(res, open(sortie, "w"), indent=2)
print("RES", json.dumps(res))
