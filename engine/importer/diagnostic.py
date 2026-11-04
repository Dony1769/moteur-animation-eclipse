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


# Os de référence de la convention Mixamo (sans préfixe). Reconnus avec ou sans « mixamorig: »
# (erreur 45 : Ara 3D Gen exporte les mêmes noms sans préfixe).
OS_MIXAMO_REF = {"Hips", "Spine", "Spine1", "Spine2", "Neck", "Head", "LeftShoulder", "LeftArm", "LeftForeArm",
                 "LeftHand", "RightShoulder", "RightArm", "RightForeArm", "RightHand", "LeftUpLeg", "LeftLeg",
                 "LeftFoot", "LeftToeBase", "RightUpLeg", "RightLeg", "RightFoot", "RightToeBase"}


def _nom_base(n):
    return n.split(":", 1)[1] if n.startswith("mixamorig:") else n


def _arm_info(a):
    os_ = [b.name for b in a.data.bones]
    mixamo = sum(1 for n in os_ if n.startswith("mixamorig:"))
    reconnus = sum(1 for n in os_ if _nom_base(n) in OS_MIXAMO_REF)
    convention = "mixamo" if reconnus >= 0.8 * len(OS_MIXAMO_REF) else "inconnue"
    return {
        "nom": a.name,
        "os": len(os_),
        "os_mixamo": mixamo,
        "os_reference_mixamo": reconnus,
        "prefixe_mixamorig": mixamo >= 0.8 * len(os_),
        "convention": convention,
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


VERSION_DIAGNOSTIC = 2


def _textures(meshes):
    """Images utilisées par les matériaux (nœuds Image Texture), sans doublon."""
    noms = set()
    for m in meshes:
        for slot in m.material_slots:
            mat = slot.material
            if not mat or not mat.use_nodes or not mat.node_tree:
                continue
            for n in mat.node_tree.nodes:
                if n.type == "TEX_IMAGE" and n.image:
                    noms.add(n.image.name)
    return sorted(noms)


def _dimensions(meshes):
    """Étendue monde X, Y, Z des sommets, en mètres."""
    if not meshes:
        return None
    xs, ys, zs = [], [], []
    for m in meshes:
        for v in m.data.vertices:
            w = m.matrix_world @ v.co
            xs.append(w.x); ys.append(w.y); zs.append(w.z)
    return {"x": round(max(xs) - min(xs), 4), "y": round(max(ys) - min(ys), 4), "z": round(max(zs) - min(zs), 4)}


def _animations():
    """Plage d'images et nombre de courbes par action (compatible Blender 4.4+ et versions antérieures)."""
    res = []
    for a in bpy.data.actions:
        courbes = len(a.fcurves) if hasattr(a, "fcurves") else None
        res.append({"nom": a.name, "images": [int(a.frame_range[0]), int(a.frame_range[1])], "courbes": courbes})
    return res


GROUPES_CORPS = {
    "tete": {"Head", "HeadTop_End", "Neck", "Jaw"},
    "tronc": {"Hips", "Spine", "Spine1", "Spine2"},
    "bras_gauche": {"LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand"},
    "bras_droit": {"RightShoulder", "RightArm", "RightForeArm", "RightHand"},
    "jambe_gauche": {"LeftUpLeg", "LeftLeg", "LeftFoot", "LeftToeBase"},
    "jambe_droite": {"RightUpLeg", "RightLeg", "RightFoot", "RightToeBase"},
}


def _parties_du_corps(armatures):
    """Parties du corps reconnues par les noms d'os. Sans armature : rien n'est déduit (pas d'invention)."""
    if not armatures:
        return {"methode": "aucune_armature", "parties": []}
    os_bases = {_nom_base(b.name) for a in armatures for b in a.data.bones}
    trouvees = [p for p, noms in GROUPES_CORPS.items() if noms & os_bases]
    return {"methode": "noms_d_os", "parties": trouvees}


def _operations(type_, rapport_poids, convention, facteur_echelle, axe_vertical=None):
    """Opérations nécessaires déduites du diagnostic (aucune n'est exécutée ici)."""
    ops = []
    if type_ == "sans_armature":
        ops += ["estimer_articulations", "generer_armature", "calculer_poids"]
    elif type_ == "armature_sans_poids":
        ops += ["calculer_poids"]
    elif type_ == "armature_et_poids":
        if rapport_poids and rapport_poids.get("sommets_sans_poids", 0) > 0:
            ops.append("completer_poids_sommets_orphelins")
        if convention != "mixamo":
            ops.append("normaliser_convention_os")
    if rapport_poids and rapport_poids.get("sommets_poids_non_normalises", 0) > 0:
        ops.append("normaliser_poids")
    if facteur_echelle is not None:
        ops.insert(0, f"normaliser_echelle_x{facteur_echelle}")
    if axe_vertical is not None and axe_vertical != "z":
        ops.insert(1, f"normaliser_axe_vertical_{axe_vertical}_vers_z")
    return ops


def analyser(chemin):
    _vider_scene()
    erreurs_import = []
    try:
        _importer(chemin)
    except Exception as e:  # on consigne l'erreur, on ne plante pas
        erreurs_import.append(f"import : {e}")
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
    elif not any(m.vertex_groups for m in meshes):
        anomalies.append("armature présente mais aucun groupe de poids")
    for m in meshes:
        if m.vertex_groups:
            pw = _poids(m)
            if pw["sommets_sans_poids"] > 0:
                pct = round(100.0 * pw["sommets_sans_poids"] / max(1, pw["sommets"]), 1)
                anomalies.append(f"{m.name} : {pw['sommets_sans_poids']} sommets sans poids ({pct} %)")
            if pw["sommets_poids_non_normalises"] > 0:
                anomalies.append(f"{m.name} : {pw['sommets_poids_non_normalises']} sommets à poids non normalisés")
    # échelle : une hauteur humaine plausible est entre 0,3 et 3 m (erreur 33 : facteur 100 ou 0,01)
    h = _taille(meshes)
    facteur = None
    axe_haut = None
    if h is not None and not (0.3 <= h <= 3.0):
        import math as _m
        facteur = 10 ** round(_m.log10(1.75 / h))
        anomalies.append(f"échelle suspecte : hauteur {h} m (facteur suggéré {facteur})")
        # axe vertical : l'axe dont l'étendue, mise à l'échelle, est une taille humaine (1,4 à 2,0 m)
        # et dont l'étendue perpendiculaire est une profondeur (< 0,5 m). Heuristique, signalée comme telle.
        dim = _dimensions(meshes)
        if dim:
            candidats = {ax: dim[ax] * facteur for ax in ("y", "z")}
            humains = [ax for ax, v in candidats.items() if 1.4 <= v <= 2.0]
            if len(humains) == 1 and candidats[("z" if humains[0] == "y" else "y")] <= 0.5:
                axe_haut = humains[0]
            elif len(humains) == 1:
                axe_haut = humains[0]
            if axe_haut is not None and axe_haut != "z":
                anomalies.append(f"axe vertical probable : {axe_haut.upper()} (au lieu de Z) : heuristique")
    for m in meshes:
        if m.vertex_groups and not m.material_slots:
            anomalies.append(f"{m.name} : pas de matériau")
    type_ = _type(meshes, armatures, actions)
    poids_global = None
    for m in meshes:
        if m.vertex_groups:
            poids_global = _poids(m)
            break
    convention = _arm_info(armatures[0])["convention"] if armatures else None
    rapport = {
        "version_diagnostic": VERSION_DIAGNOSTIC,
        "fichier": chemin,
        "type": type_,
        "erreurs_import": erreurs_import,
        "dimensions_m": _dimensions(meshes),
        "textures": _textures(meshes),
        "parties_du_corps": _parties_du_corps(armatures),
        "operations_recommandees": _operations(type_, poids_global, convention, facteur, axe_haut),
        "facteur_echelle_suggere": facteur,
        "axe_vertical_suggere": axe_haut,
        "objets": [o.name for o in objets],
        "meshes": [_mesh_info(m) for m in meshes],
        "armatures": [_arm_info(a) for a in armatures],
        "actions": actions,
        "animations": _animations(),
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
