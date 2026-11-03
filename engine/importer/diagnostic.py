"""Diagnostic d'un personnage (FBX ou .blend) : rapport JSON, sans modifier le fichier source.

Lancé dans Blender en mode headless :
    blender -b --factory-startup --disable-autoexec -P engine/importer/diagnostic.py -- ENTREE.fbx SORTIE.json

Ce module ne fait que LIRE : il décrit géométrie, UV, matériaux, armature, poids, animations, et signale
les anomalies. Il ne corrige rien (les corrections seront des étapes séparées, testées une à une).
"""
import json
import math
import sys

import bpy


def _vider_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def _importer(chemin):
    if chemin.lower().endswith(".fbx"):
        bpy.ops.import_scene.fbx(filepath=chemin, automatic_bone_orientation=True)
    elif chemin.lower().endswith(".blend"):
        with bpy.data.libraries.load(chemin, link=False) as (src, dst):
            dst.objects = list(src.objects)
        for o in dst.objects:
            if o is not None:
                bpy.context.scene.collection.objects.link(o)
    else:
        raise ValueError("format non pris en charge : " + chemin)


def _poids(mesh_obj):
    """Influences par sommet : nombre de groupes non nuls, sommets sans groupe, somme des poids."""
    mesh = mesh_obj.data
    sans_groupe = 0
    max_influences = 0
    sommes_hors_norme = 0
    total = 0
    for v in mesh.vertices:
        poids = [g.weight for g in v.groups if g.weight > 0.0]
        total += 1
        if not poids:
            sans_groupe += 1
            continue
        max_influences = max(max_influences, len(poids))
        if abs(sum(poids) - 1.0) > 0.01:
            sommes_hors_norme += 1
    return {
        "sommets": total,
        "sommets_sans_poids": sans_groupe,
        "max_influences_par_sommet": max_influences,
        "sommets_poids_non_normalises": sommes_hors_norme,
        "groupes_de_sommets": len(mesh_obj.vertex_groups),
    }


def _mesh_info(o):
    mesh = o.data
    tris = sum(1 for p in mesh.polygons if len(p.vertices) == 3)
    quads = sum(1 for p in mesh.polygons if len(p.vertices) == 4)
    ngones = sum(1 for p in mesh.polygons if len(p.vertices) > 4)
    armature_mod = [m for m in o.modifiers if m.type == "ARMATURE"]
    return {
        "nom": o.name,
        "sommets": len(mesh.vertices),
        "faces": len(mesh.polygons),
        "triangles": tris,
        "quads": quads,
        "ngones": ngones,
        "uv_calques": [uv.name for uv in mesh.uv_layers],
        "materiaux": [s.material.name for s in o.material_slots if s.material],
        "modificateur_armature": armature_mod[0].object.name if armature_mod and armature_mod[0].object else None,
        "parent": o.parent.name if o.parent else None,
        "parent_type": o.parent_type if o.parent else None,
        "parent_os": (o.parent_bone or None) if o.parent else None,
        "poids": _poids(o) if o.vertex_groups else None,
    }


def _arm_info(a):
    os_ = [b.name for b in a.data.bones]
    mixamo = sum(1 for n in os_ if n.startswith("mixamorig:"))
    return {
        "nom": a.name,
        "os": len(os_),
        "os_mixamo": mixamo,
        "convention": "mixamo" if mixamo and mixamo >= 0.8 * len(os_) else "inconnue",
        "racine": [b.name for b in a.data.bones if b.parent is None],
        "echelle": tuple(round(v, 4) for v in a.scale),
        "rotation_base_deg": tuple(round(math.degrees(v), 2) for v in a.rotation_euler),
    }


def _taille(meshes):
    """Hauteur du personnage : étendue verticale des sommets dans le monde."""
    zs = []
    for m in meshes:
        zs += [(m.matrix_world @ v.co).z for v in m.data.vertices]
    if not zs:
        return None
    return round(max(zs) - min(zs), 4)


def _type(meshes, armatures, anims):
    if not armatures and meshes:
        return "sans_armature"
    if armatures and meshes:
        avec_poids = [m for m in meshes if m.vertex_groups]
        if not avec_poids:
            return "armature_sans_poids"
        return "armature_et_poids"
    return "inconnu"


def analyser(chemin):
    _vider_scene()
    _importer(chemin)
    objets = list(bpy.data.objects)
    meshes = [o for o in objets if o.type == "MESH"]
    armatures = [o for o in objets if o.type == "ARMATURE"]
    actions = [a.name for a in bpy.data.actions]
    anomalies = []
    cubes = [m.name for m in meshes if m.name.lower().startswith("cube")]
    if cubes:
        anomalies.append("primitive parasite présente : " + ", ".join(cubes))
    for m in meshes:
        if m.vertex_groups and not any(mod.type == "ARMATURE" for mod in m.modifiers):
            anomalies.append(f"{m.name} : groupes de poids mais pas de modificateur Armature")
        if m.data.uv_layers == [] or len(m.data.uv_layers) == 0:
            anomalies.append(f"{m.name} : aucune UV")
        if m.data.polygons and sum(1 for p in m.data.polygons if len(p.vertices) > 4):
            anomalies.append(f"{m.name} : n-gones présents")
    if not armatures:
        anomalies.append("aucune armature")
    for m in meshes:
        if m.vertex_groups and not m.material_slots:
            anomalies.append(f"{m.name} : pas de matériau")
    rapport = {
        "fichier": chemin,
        "type": _type(meshes, armatures, actions),
        "objets": [o.name for o in objets],
        "meshes": [_mesh_info(m) for m in meshes],
        "armatures": [_arm_info(a) for a in armatures],
        "actions": actions,
        "hauteur_m": _taille(meshes),
        "anomalies": anomalies,
        "cles_de_forme": [kb.name for m in meshes if m.data.shape_keys
                          for kb in m.data.shape_keys.key_blocks],
    }
    return rapport


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:]
    entree, sortie = argv[0], argv[1]
    rapport = analyser(entree)
    with open(sortie, "w") as f:
        json.dump(rapport, f, indent=2, ensure_ascii=False)
    print("DIAGNOSTIC_OK", rapport["type"], "meshes", len(rapport["meshes"]), "armatures", len(rapport["armatures"]),
          "anomalies", len(rapport["anomalies"]))
