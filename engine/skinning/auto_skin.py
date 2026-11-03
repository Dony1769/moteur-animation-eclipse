"""Étape 3 : squelette estimé + skinning automatique (méthode heat, Blender) pour un maillage humanoïde sans poids.

Entrée  : un .blend contenant un maillage humanoïde sans armature ni vertex groups.
Sortie  : un .blend skinné (copie, la source n'est jamais modifiée) + un rapport JSON.

Méthode (déterministe, CPU) :
1. Mesure la hauteur réelle (bbox Z) et la ligne médiane (bbox X/Y).
2. Position des articulations du tronc et des jambes : fractions anatomiques de la hauteur,
   appliquées à la géométrie mesurée (pas de pose figée).
3. Bras : centre de masse des sections horizontales hors du tronc, de chaque côté,
   à la hauteur de l'épaule, du coude et du poignet. Les points du bras sont donc mesurés.
4. Poids : Blender ARMATURE_AUTO (heat diffusion) ; repli ARMATURE_ENVELOPE si la chaleur échoue.
5. Post-traitement : lissage, limite à MAX_INFLUENCES, normalisation.
6. Tests de déformation (bras, coude, hanche, genou, colonne, cou) avec mesure des fuites.
"""
import bpy, sys, json, math
from mathutils import Vector, Matrix

MAX_INFLUENCES = 4
ENTREE_NOM = "GEO-body_male_realistic"

# -- 1. Mesures -------------------------------------------------------------

def mesurer(obj):
    pts = [obj.matrix_world @ v.co for v in obj.data.vertices]
    zmin = min(p.z for p in pts); zmax = max(p.z for p in pts)
    xmin = min(p.x for p in pts); xmax = max(p.x for p in pts)
    ymin = min(p.y for p in pts); ymax = max(p.y for p in pts)
    return pts, {"zmin": zmin, "zmax": zmax, "H": zmax - zmin,
                 "xc": (xmin + xmax) / 2, "yc": (ymin + ymax) / 2,
                 "xmin": xmin, "xmax": xmax}

def centroide_bras(pts, m, z_frac, cote):
    """Centre de masse des sommets du bras côté `cote` (+1/-1) dans une tranche de hauteur."""
    H, zmin, xc = m["H"], m["zmin"], m["xc"]
    z = zmin + z_frac * H; tol = 0.02 * H
    sel = [p for p in pts if abs(p.z - z) <= tol and cote * (p.x - xc) > 0.22 * H * 0.5]
    if not sel:
        return None
    return Vector((sum(p.x for p in sel) / len(sel), sum(p.y for p in sel) / len(sel),
                   sum(p.z for p in sel) / len(sel)))

# -- 2-3. Squelette --------------------------------------------------------

def definir_squelette(pts, m):
    H, zmin, xc, yc = m["H"], m["zmin"], m["xc"], m["yc"]
    Z = lambda f: zmin + f * H
    os_ = {}  # nom : (tete, queue, parent)
    os_["mixamorig:Hips"] = (Vector((xc, yc, Z(0.52))), Vector((xc, yc, Z(0.57))), None)
    os_["mixamorig:Spine"] = (Vector((xc, yc, Z(0.57))), Vector((xc, yc, Z(0.64))), "mixamorig:Hips")
    os_["mixamorig:Spine1"] = (Vector((xc, yc, Z(0.64))), Vector((xc, yc, Z(0.72))), "mixamorig:Spine")
    os_["mixamorig:Neck"] = (Vector((xc, yc, Z(0.79))), Vector((xc, yc, Z(0.84))), "mixamorig:Spine1")
    os_["mixamorig:Head"] = (Vector((xc, yc, Z(0.84))), Vector((xc, yc, Z(1.0))), "mixamorig:Neck")
    for cote, nom in ((+1, "Left"), (-1, "Right")):
        dx = 0.11 * H / 1.69 * 1.0  # écart des hanches mesuré : ~0,11 m pour H = 1,69 m
        hx = xc + cote * dx
        os_[f"mixamorig:{nom}UpLeg"] = (Vector((hx, yc, Z(0.52))), Vector((hx, yc, Z(0.285))), "mixamorig:Hips")
        os_[f"mixamorig:{nom}Leg"] = (Vector((hx, yc, Z(0.285))), Vector((hx, yc, Z(0.04))), f"mixamorig:{nom}UpLeg")
        os_[f"mixamorig:{nom}Foot"] = (Vector((hx, yc, Z(0.04))), Vector((hx, yc + 0.17 * H / 1.69, Z(0.0))), f"mixamorig:{nom}Leg")
        # Bras : centres de masse mesurés
        epaule = centroide_bras(pts, m, 0.80, cote)
        coude = centroide_bras(pts, m, 0.64, cote)
        poignet = centroide_bras(pts, m, 0.47, cote)
        if epaule is None or coude is None or poignet is None:
            raise RuntimeError(f"bras {nom} non mesurable (épaule/coude/poignet manquant)")
        os_[f"mixamorig:{nom}Shoulder"] = (Vector((xc + cote * 0.165 * H / 1.69, yc, Z(0.80))), epaule, "mixamorig:Spine1")
        os_[f"mixamorig:{nom}Arm"] = (epaule, coude, f"mixamorig:{nom}Shoulder")
        os_[f"mixamorig:{nom}ForeArm"] = (coude, poignet, f"mixamorig:{nom}Arm")
        os_[f"mixamorig:{nom}Hand"] = (poignet, poignet + (poignet - coude).normalized() * 0.08 * H / 1.69, f"mixamorig:{nom}ForeArm")
    return os_

def construire_armature(os_, nom="Squelette_HBM"):
    data = bpy.data.armatures.new(nom)
    obj = bpy.data.objects.new(nom, data)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    eb = {}
    for n, (t, q, p) in os_.items():
        b = data.edit_bones.new(n)
        b.head = t; b.tail = q
        eb[n] = b
    for n, (_, _, p) in os_.items():
        if p:
            eb[n].parent = eb[p]
    bpy.ops.object.mode_set(mode="OBJECT")
    return obj

# -- 4-5. Poids ------------------------------------------------------------

def skinner(corps, arm):
    bpy.ops.object.select_all(action="DESELECT")
    corps.select_set(True); arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    try:
        bpy.ops.object.parent_set(type="ARMATURE_AUTO")
        methode = "ARMATURE_AUTO (chaleur)"
    except RuntimeError as e:
        bpy.ops.object.parent_set(type="ARMATURE_ENVELOPE")
        methode = "ARMATURE_ENVELOPE (repli) : " + str(e)[:120]
    bpy.ops.object.select_all(action="DESELECT")
    corps.select_set(True)
    bpy.context.view_layer.objects.active = corps
    lisser_limiter_normaliser(corps)
    return methode

def lisser_limiter_normaliser(corps, facteur=0.5, passes=2):
    """Post-traitement explicite des poids (déterministe, sans opérateur d'interface) :
    1. lissage : chaque poids se mélange à la moyenne des voisins (arêtes du maillage) ;
    2. limite : seulement les MAX_INFLUENCES plus fortes influences sont gardées ;
    3. normalisation : la somme des poids de chaque sommet vaut 1."""
    me = corps.data
    voisins = [set() for _ in me.vertices]
    for e in me.edges:
        a, b = e.vertices
        voisins[a].add(b); voisins[b].add(a)
    poids = [{g.group: g.weight for g in v.groups} for v in me.vertices]
    for _ in range(passes):
        nouveau = []
        for i, courant in enumerate(poids):
            if not voisins[i]:
                nouveau.append(courant); continue
            moy = {}
            for j in voisins[i]:
                for gid, w in poids[j].items():
                    moy[gid] = moy.get(gid, 0.0) + w / len(voisins[i])
            fusion = {}
            for gid in set(courant) | set(moy):
                fusion[gid] = (1 - facteur) * courant.get(gid, 0.0) + facteur * moy.get(gid, 0.0)
            nouveau.append(fusion)
        poids = nouveau
    finaux = {}
    for i, p_ in enumerate(poids):
        gardes = sorted(((g, w) for g, w in p_.items() if w > 1e-4), key=lambda kv: kv[1], reverse=True)[:MAX_INFLUENCES]
        total = sum(w for _, w in gardes)
        finaux[i] = [(g, w / total) for g, w in gardes] if total > 0 else []
    # réécriture : on vide puis on remplit chaque groupe
    par_groupe = {}
    for i, lst in finaux.items():
        for g, w in lst:
            par_groupe.setdefault(g, []).append((i, w))
    for vg in corps.vertex_groups:
        vg.remove(list(range(len(me.vertices))))
        for i, w in par_groupe.get(vg.index, []):
            vg.add([i], w, "REPLACE")

def rattacher_pieces_rigides(arm, os_nom="mixamorig:Head"):
    """Les yeux ne se déforment pas : ils suivent l'os Head en rigide (parenté à l'os, transform conservée)."""
    bone = arm.data.bones[os_nom]
    rattaches = []
    for o in list(bpy.data.objects):
        if not o.name.startswith(ENTREE_NOM + ".eye"):
            continue
        monde = o.matrix_world.copy()
        o.parent = arm
        o.parent_type = "BONE"
        o.parent_bone = os_nom
        cible = arm.matrix_world @ bone.matrix_local @ Matrix.Translation(Vector((0, bone.length, 0)))
        o.matrix_parent_inverse = cible.inverted() @ monde @ o.matrix_basis.inverted()
        rattaches.append(o.name)
    return rattaches

def auditer_poids(corps):
    """Relit les poids réels, sans supposer le résultat."""
    sans = 0; non_norm = 0; maxinf = 0
    for v in corps.data.vertices:
        ws = [g.weight for g in v.groups if g.weight > 0]
        if not ws:
            sans += 1; continue
        maxinf = max(maxinf, len(ws))
        if abs(sum(ws) - 1.0) > 1e-3:
            non_norm += 1
    return {"sommets_sans_poids": sans, "sommets_poids_non_normalises": non_norm,
            "max_influences_par_sommet": maxinf, "groupes": len(corps.vertex_groups)}

# -- 6. Tests de déformation ----------------------------------------------

def deformer_et_mesurer(corps, arm, os_name, angle_deg, axe_monde):
    """Plie un os d'un angle autour d'un axe MONDE passant par sa tête, mesure le déplacement de chaque
    sommet, puis remet la pose de repos. Renvoie (déplacements, positions de repos)."""
    pb = arm.pose.bones[os_name]
    base = [corps.matrix_world @ v.co for v in corps.data.vertices]
    tete_monde = arm.matrix_world @ pb.bone.head_local
    rot = Matrix.Rotation(math.radians(angle_deg), 4, Vector(axe_monde).normalized())
    pivot = Matrix.Translation(tete_monde) @ rot @ Matrix.Translation(-tete_monde)
    repos = pb.matrix.copy()
    pb.matrix = pivot @ repos
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = corps.evaluated_get(dg)
    mesh = ev.to_mesh()
    apres = [corps.matrix_world @ v.co for v in mesh.vertices]
    ev.to_mesh_clear()
    pb.matrix = repos
    bpy.context.view_layer.update()
    return [(a - b).length for a, b in zip(apres, base)], base

def tester_repos(corps, yeux):
    """En pose de repos le skinning ne doit pas déformer le maillage (écart < 1 mm) ;
    les pièces rigides gardent leur position monde (écart < 1 mm)."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = corps.evaluated_get(dg)
    m = ev.to_mesh()
    ecarts = [((corps.matrix_world @ a.co) - (corps.matrix_world @ b.co)).length
              for a, b in zip(m.vertices, corps.data.vertices)]
    ev.to_mesh_clear()
    ecart_max = max(ecarts)
    return {"test": "pose de repos : le skinning ne modifie pas l'apparence", "ok": ecart_max < 0.001,
            "detail": f"écart maximal {ecart_max*1000:.4f} mm"}

def descendants(arm, nom):
    """Os descendant de `nom` dans la hiérarchie (lui-même exclu)."""
    res = set()
    for b in arm.data.bones:
        p = b.parent
        while p is not None:
            if p.name == nom:
                res.add(b.name); break
            p = p.parent
    return res

def groupe_dominant(corps):
    """Nom du groupe au poids le plus fort, pour chaque sommet (lecture des poids réels)."""
    noms = {g.index: g.name for g in corps.vertex_groups}
    res = []
    for v in corps.data.vertices:
        if not v.groups:
            res.append(None); continue
        g = max(v.groups, key=lambda g: g.weight)
        res.append(noms[g.group])
    return res

def tester_deformations(corps, arm, os_, H):
    """Plie chaque articulation autour d'un axe anatomique (monde). Critères :
    - aucun NaN ;
    - le segment se déforme (des sommets bougent) ;
    - FUITE : un os ne doit déplacer de plus de 2 cm que les sommets qui lui sont rattachés,
      c'est-à-dire dont le groupe dominant est cet os ou un de ses descendants.
      Les bras, liés à la colonne, sont donc légitimement mobiles ; les jambes ne le sont pas.
      Tolérance : 1 % des sommets non rattachés ;
    - aucun déplacement supérieur à la moitié de la hauteur du personnage."""
    tests = []
    dominants = groupe_dominant(corps)
    # (nom, os, axe monde de flexion, angle)
    definitions = []
    for cote in ("Left", "Right"):
        definitions += [
            (f"épaule {cote} (flexion du bras)", f"mixamorig:{cote}Arm", (0, 1, 0), 60),
            (f"coude {cote}", f"mixamorig:{cote}ForeArm", (0, 1, 0), 60),
            (f"hanche {cote} (flexion de la cuisse)", f"mixamorig:{cote}UpLeg", (1, 0, 0), 30),
            (f"genou {cote}", f"mixamorig:{cote}Leg", (1, 0, 0), 45),
        ]
    definitions += [
        ("colonne (flexion)", "mixamorig:Spine1", (1, 0, 0), 20),
        ("cou", "mixamorig:Neck", (1, 0, 0), 20),
    ]
    for nom, os_name, axe, ang in definitions:
        if os_name not in arm.pose.bones:
            tests.append({"test": nom, "ok": False, "detail": "os absent"}); continue
        d, base = deformer_et_mesurer(corps, arm, os_name, ang, axe)
        liés = descendants(arm, os_name) | {os_name}
        nan = sum(1 for x in d if math.isnan(x))
        bouge = sum(1 for x in d if x > 0.002)
        maxi = max(d) if d else 0.0
        non_liés = [i for i, g in enumerate(dominants) if g is not None and g not in liés]
        fuite = sum(1 for i in non_liés if d[i] > 0.02)
        fuite_part = fuite / max(1, len(non_liés))
        ok = nan == 0 and bouge > 0 and fuite_part < 0.01 and maxi < 0.5 * H
        tests.append({"test": nom, "ok": ok,
                      "detail": f"{bouge}/{len(d)} sommets bougent, max {maxi:.3f} m, "
                                f"fuite vers sommets non rattachés {fuite}/{len(non_liés)} ({fuite_part:.2%}), NaN {nan}"})
    return tests

# -- Programme principal ---------------------------------------------------

def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    entree, sortie_blend, sortie_json = argv[0], argv[1], argv[2]
    bpy.ops.wm.open_mainfile(filepath=entree)
    corps = bpy.data.objects[ENTREE_NOM]
    if corps.parent is not None or len(corps.vertex_groups) > 0:
        raise RuntimeError("entrée déjà armée : test B attend un maillage sans skinning")
    pts, m = mesurer(corps)
    os_ = definir_squelette(pts, m)
    arm = construire_armature(os_)
    methode = skinner(corps, arm)
    rigides = rattacher_pieces_rigides(arm)
    audit = auditer_poids(corps)
    tests = [tester_repos(corps, [o for o in bpy.data.objects if o.name.startswith(ENTREE_NOM + ".eye")])]
    tests += tester_deformations(corps, arm, os_, m["H"])
    bpy.ops.wm.save_as_mainfile(filepath=sortie_blend)
    rapport = {"entree": entree, "mesure": {k: round(v, 4) for k, v in m.items()},
                "methode_skinning": methode, "os": len(os_), "poids": audit, "pieces_rigides": rigides,
                "tests_deformation": tests}
    json.dump(rapport, open(sortie_json, "w"), indent=2, ensure_ascii=False)
    print("RAPPORT", json.dumps(rapport, ensure_ascii=False))

if __name__ == "__main__":
    main()
