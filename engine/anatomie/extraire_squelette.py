"""Extraction anatomique réelle d'une armature et de son maillage (phase 4, étape 1).

Exécution (Blender 4.5 LTS, sans écrire dans le fichier source) :
  blender -b --factory-startup --disable-autoexec -P extraire_squelette.py -- ENTREE SORTIE_JSON SORTIE_NPZ

ENTREE : .fbx (importé) ou .blend (ouvert en lecture).

Données extraites, toutes lues dans l'armature, aucune valeur de remplacement :
- longueur de chaque os (queue − tête, repos, espace monde, mètres) ;
- parent / enfants (relations réelles) ;
- tête, queue, axes locaux (matrice de repos, colonnes X, Y, Z en monde) ;
- os sans enfant : longueur non déduite, signalée « feuille » ;
- poids par sommet (groupes de sommets Blender, normalisés à la somme) ;
- avertissements : unité, échelle, axes absents ou ambigus.

Remarque : le nom des os n'est PAS utilisé pour classer les régions : la classification passe par la topologie
(profondeur, ascendants, nombre d'enfants) dans analyser_topologie.py.
"""
import bpy
import json
import sys

import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:]
entree, sortie_json, sortie_npz = argv[0], argv[1], argv[2]

bpy.ops.wm.read_factory_settings(use_empty=True)
if entree.lower().endswith(".fbx"):
    bpy.ops.import_scene.fbx(filepath=entree)
else:
    bpy.ops.wm.open_mainfile(filepath=entree)

avertissements = []

armatures = [o for o in bpy.data.objects if o.type == "ARMATURE"]
if not armatures:
    raise SystemExit("aucune armature dans le fichier")
arm = max(armatures, key=lambda o: len(o.data.bones))
if len(armatures) > 1:
    avertissements.append(f"{len(armatures)} armatures : la plus grande ({arm.name}) est utilisée")

M = arm.matrix_world
bones = list(arm.data.bones)
noms = [b.name for b in bones]
index = {n: i for i, n in enumerate(noms)}

os_data = []
for b in bones:
    tete = np.array(M @ b.head_local)
    queue = np.array(M @ b.tail_local)
    rot = np.array(M.to_3x3()) @ np.array(b.matrix_local.to_3x3())
    enfants = [c.name for c in b.children]
    longueur = float(np.linalg.norm(queue - tete))
    os_data.append({
        "nom": b.name,
        "parent": b.parent.name if b.parent else None,
        "enfants": enfants,
        "tete": tete.tolist(),
        "queue": queue.tolist(),
        "longueur": longueur,
        "axe_x": rot[:, 0].tolist(),
        "axe_y": rot[:, 1].tolist(),
        "axe_z": rot[:, 2].tolist(),
        "feuille": len(enfants) == 0,
        # Un os terminal n'a pas de cible : Blender lui recopie souvent la longueur du parent (vérifié sur Maria :
        # LeftHandThumb4 = LeftHandThumb3 = 0,0333 m). Sa longueur n'est donc pas une mesure anatomique.
        "longueur_fiable": len(enfants) > 0,
    })
    if longueur < 1e-6:
        avertissements.append(f"os {b.name} de longueur nulle")

# Unités et axes : signalés, non supposés.
scene = bpy.context.scene
u = scene.unit_settings
infos_unite = {
    "scale_length": u.scale_length,
    "system": u.system,
    "echelle_objet_armature": list(arm.scale),
}
if abs(u.scale_length - 1.0) > 1e-9:
    avertissements.append(f"scale_length={u.scale_length} : longueurs déjà en mètres ? vérifier")

# Maillages déformés par l'armature.
def _deforme_par_arm(o):
    """Maillage lié par modificateur, ou à défaut dont la majorité des groupes de sommets nomment un os."""
    if any(m.type == "ARMATURE" and m.object == arm for m in o.modifiers):
        return True
    groupes = [g.name for g in o.vertex_groups]
    return len(groupes) > 0 and sum(n in index for n in groupes) >= 0.5 * len(groupes)


meshes = [o for o in bpy.data.objects if o.type == "MESH" and _deforme_par_arm(o)]
if len(argv) > 3:
    # Sélection explicite par nom (ex. GEO-body_female_realistic) : un fichier peut contenir plusieurs corps.
    voulus = argv[3].split(",")
    meshes = [o for o in meshes if o.name in voulus]
    manquants = [n for n in voulus if n not in [o.name for o in meshes]]
    if manquants:
        avertissements.append(f"maillages demandés introuvables : {manquants}")
elif len(meshes) > 1:
    avertissements.append(f"{len(meshes)} maillages déformables sans sélection : {[o.name for o in meshes]}")
if not meshes:
    avertissements.append("aucun maillage déformé par cette armature : poids non extraits")
else:
    liaison = [o.name for o in meshes if not any(m.type == "ARMATURE" for m in o.modifiers)]
    if liaison:
        avertissements.append(f"maillages sans modificateur Armature (liés par groupes seulement) : {liaison}")

sommets, poids_lignes, groupes = [], [], []
for mesh_obj in meshes:
    mesh = mesh_obj.data
    Mm = mesh_obj.matrix_world
    noms_groupes = {g.index: g.name for g in mesh_obj.vertex_groups}
    for v in mesh.vertices:
        co = Mm @ v.co
        ligne = np.zeros(len(noms))
        for g in v.groups:
            nom = noms_groupes.get(g.group)
            if nom in index and g.weight > 0:
                ligne[index[nom]] += g.weight
        s = ligne.sum()
        if s > 0:
            ligne = ligne / s
        sommets.append(np.array(co))
        poids_lignes.append(ligne)
    groupes.append({"maillage": mesh_obj.name, "sommets": len(mesh.vertices)})

    # Groupes sans os correspondant : signalés.
    absents = [n for n in noms_groupes.values() if n not in index]
    if absents:
        avertissements.append(f"{mesh_obj.name} : groupes sans os : {absents[:8]}")

if sommets:
    sommets = np.array(sommets, dtype=np.float64)
    poids = np.array(poids_lignes, dtype=np.float32)
    sans_poids = int((poids.sum(axis=1) == 0).sum())
    if sans_poids:
        avertissements.append(f"{sans_poids} sommets sans poids (non déformés)")
    np.savez_compressed(sortie_npz, sommets=sommets, poids=poids, noms_os=np.array(noms))
else:
    np.savez_compressed(sortie_npz, sommets=np.zeros((0, 3)), poids=np.zeros((0, len(noms))),
                        noms_os=np.array(noms))

sortie = {
    "entree": entree,
    "nb_os": len(noms),
    "nb_sommets": len(sommets) if len(sommets) else 0,
    "maillages": groupes,
    "unite": infos_unite,
    "os": os_data,
    "avertissements": avertissements,
}
with open(sortie_json, "w", encoding="utf-8") as f:
    json.dump(sortie, f, ensure_ascii=False, indent=1)
print(f"OK {entree} : {len(noms)} os, {sortie['nb_sommets']} sommets, {len(avertissements)} avertissement(s)")
