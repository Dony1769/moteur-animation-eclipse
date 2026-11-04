"""Test B, items 1 à 4 : corps HBM sans skinning (mesh seul).

1. Import du mesh (objet GEO-body_male_realistic extrait du bundle, source non modifiée).
2. Absence de skinning : aucun modificateur Armature, aucun groupe de sommets, aucun parent (un modificateur Multires est présent : ce n'est pas du skinning).
3. Géométrie : sommets, faces, part des quads/tris/n-gones, bords ouverts (maillage fermé ?), UV.
4. Dimensions monde : hauteur, envergure X (bras écartés, pas la largeur d'épaules), profondeur.
Usage : blender -b --factory-startup --disable-autoexec -P engine/validation/test_hbm_corps.py -- BUNDLE.blend SORTIE.json SCRATCH
"""
import bpy, bmesh, sys, json, os, shutil

argv = sys.argv[sys.argv.index("--") + 1:]
bundle, sortie, scratch = argv[0], argv[1], argv[2]
os.makedirs(scratch, exist_ok=True)
copie = os.path.join(scratch, "bundle.blend")
shutil.copy(bundle, copie)
bpy.ops.wm.open_mainfile(filepath=copie)
NOM = "GEO-body_male_realistic"
res = {"tests": {}, "geometrie": {}, "dimensions_m": {}}
T = res["tests"]
def ok(n, c, d="", statut=None):
    T[n] = {"ok": bool(c), "detail": d, "statut": statut or ("ok" if c else "echec")}

o = bpy.data.objects.get(NOM)
ok("1_import", o is not None and o.type == "MESH", f"objet {NOM} {'trouvé' if o else 'absent'}")
if o is None:
    json.dump(res, open(sortie, "w"), indent=2, ensure_ascii=False); raise SystemExit(1)
m = o.data
ok("2_pas_de_skinning",
   not any(md.type == "ARMATURE" for md in o.modifiers) and len(o.vertex_groups) == 0 and o.parent is None,
   f"modificateurs {[md.type for md in o.modifiers]}, groupes {len(o.vertex_groups)}, parent {o.parent.name if o.parent else None}")

bm = bmesh.new(); bm.from_mesh(m)
nb = sum(1 for e in bm.edges if e.is_boundary)
nq = sum(1 for f in bm.faces if len(f.verts) == 4)
nt = sum(1 for f in bm.faces if len(f.verts) == 3)
nn = sum(1 for f in bm.faces if len(f.verts) > 4)
bm.free()
res["geometrie"] = {"sommets": len(m.vertices), "faces": len(m.polygons), "quads": nq, "tris": nt, "ngones": nn,
                    "bords_ouverts": nb, "uv_calques": [u.name for u in m.uv_layers], "materiaux": [s.material.name for s in o.material_slots if s.material]}
ok("3_geometrie", len(m.vertices) > 1000 and nb == 0 and len(m.uv_layers) > 0,
   f"{len(m.vertices)} sommets, {len(m.polygons)} faces (quads {nq}, tris {nt}, n-gones {nn}), bords ouverts {nb}, UV {len(m.uv_layers)}")
pts = [o.matrix_world @ v.co for v in m.vertices]
xs, ys, zs = [p.x for p in pts], [p.y for p in pts], [p.z for p in pts]
h, l, p = max(zs) - min(zs), max(xs) - min(xs), max(ys) - min(ys)
res["dimensions_m"] = {"hauteur": round(h, 4), "envergure_x_bras": round(l, 4), "profondeur_y": round(p, 4), "z_min": round(min(zs), 4)}
ok("4_dimensions", 1.5 < h < 2.0, f"hauteur {h:.3f} m, envergure X (bras écartés) {l:.3f} m, profondeur {p:.3f} m, pied à z={min(zs):.3f}")
json.dump(res, open(sortie, "w"), indent=2, ensure_ascii=False)
print("RESULTAT", "OK" if all(v["ok"] for v in T.values()) else "ECHEC " + ",".join(k for k, v in T.items() if not v["ok"]))
for k, v in T.items(): print("TEST", k, v)
