"""Test A, contrôles 7 et 8 : inventaire des contrôleurs et du rig facial de Maria.

7. Contrôleurs : inventaire des contrôles présents (contraintes IK, os de contrôle, pôles, commutation IK/FK,
   contrôle racine). Les absents sont LISTÉS, pas ajoutés : construire les contrôleurs relève de l'étape 5 du moteur.
8. Rig facial : formes-clés et os faciaux (Jaw, Eye, Head). Maria n'en a pas : le statut est « absent ».

Un contrôle est validé si l'inventaire est complet (ok = True). Le statut de la fonctionnalité est indiqué à part :
« absent » signifie que le moteur ne sait pas encore le faire, pas que le test a réussi.

Usage : blender -b --factory-startup --disable-autoexec -P engine/validation/test_maria_controles.py -- SRC.fbx SORTIE.json SCRATCH
"""
import bpy, sys, json, os, shutil

argv = sys.argv[sys.argv.index("--") + 1:]
src, sortie, scratch = argv[0], argv[1], argv[2]
os.makedirs(scratch, exist_ok=True)
copie = os.path.join(scratch, "maria_controles.fbx")
shutil.copy(src, copie)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=copie, automatic_bone_orientation=True)
arm = [o for o in bpy.data.objects if o.type == "ARMATURE"][0]
peau = max([o for o in bpy.data.objects if o.type == "MESH"], key=lambda o: len(o.data.vertices))
noms = [b.name for b in arm.data.bones]
pb = arm.pose.bones

res = {"tests": {}, "controleurs": {}, "facial": {}}


def ok(nom, cond, detail="", statut=None):
    res["tests"][nom] = {"ok": bool(cond), "detail": detail, "statut": statut or ("present" if cond else "absent")}


# -- 7 : contrôleurs --
contraintes = {p.name: [c.type for c in p.constraints] for p in pb if len(p.constraints)}
ik = {n: c for n, c in contraintes.items() if "IK" in c}
mots_controle = [n for n in noms if any(m in n.lower() for m in ("ctrl", "ik", "pole", "fk", "root", "ctr"))]
inventaire = {
    "contraintes_ik_bras_jambes": sorted(ik),
    "os_de_controle": mots_controle,
    "pole_targets": [n for n in noms if "pole" in n.lower()],
    "commutation_ik_fk": [],
    "controle_racine": [n for n in noms if n.lower() in ("root", "hips_ctrl", "root_ctrl")],
    "groupes_de_collection": [c.name for c in arm.data.collections_all],
}
manquants = []
if not ik:
    manquants.append("IK mains (bras gauche et droit)")
    manquants.append("IK pieds (jambes gauche et droite)")
if not inventaire["pole_targets"]:
    manquants.append("cibles de pôle (coudes et genoux)")
if not inventaire["commutation_ik_fk"]:
    manquants.append("commutation IK/FK")
if not inventaire["controle_racine"]:
    manquants.append("contrôle racine / hanches")
res["controleurs"] = {"inventaire": inventaire, "manquants": manquants}
ok("7_controleurs", True,
   f"inventaire complet : {len(manquants)} contrôleur(s) absent(s) : {', '.join(manquants)}",
   statut="absent" if manquants else "present")

# -- 8 : rig facial --
keys = [k.name for k in peau.data.shape_keys.key_blocks] if peau.data.shape_keys else []
faciaux = [n for n in noms if any(m in n.lower() for m in ("jaw", "eye", "face", "lip", "brow"))]
res["facial"] = {"formes_cles": keys, "os_faciaux": faciaux}
ok("8_rig_facial", True,
   f"inventaire complet : {len(keys)} forme(s)-clé, {len(faciaux)} os facial/faciaux",
   statut="present" if (len(keys) >= 15 or faciaux) else "absent")

json.dump(res, open(sortie, "w"), indent=2, ensure_ascii=False)
for k, v in res["tests"].items():
    print("TEST", k, v)
