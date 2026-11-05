import numpy as np, trimesh
exec(open('volume_genou.py').read().split("S = '/tmp")[0])
def mesure_dec(th, dec):
    R = Rot.from_rotvec(ax*np.radians(th)).as_matrix()
    P = rest0.copy(); P[F_mask] = rest0[F_mask] @ R.T + (c - R @ c) + dec
    bU = piece(U_mask, P); bF = piece(F_mask, P)
    sph = trimesh.creation.icosphere(subdivisions=3, radius=0.07); sph.apply_translation(c)
    Ur = trimesh.boolean.difference([bU, sph], engine="manifold")
    Fr = trimesh.boolean.difference([bF, sph], engine="manifold")
    it = trimesh.boolean.intersection([Ur, Fr], engine="manifold")
    return it.volume*1e6 if len(it.faces) else 0.0
for nom, d in {"+X":[1,0,0],"-X":[-1,0,0],"+Y":[0,1,0],"-Y":[0,-1,0],"+Z":[0,0,1],"-Z":[0,0,-1]}.items():
    print("témoin genou", nom, "10 cm, 120 deg :", round(mesure_dec(120, np.array(d,float)*0.10),3), "cm3", flush=True)
