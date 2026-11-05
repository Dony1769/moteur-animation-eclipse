exec(open('plis_surface_unie.py').read().split('for th in (30')[0])
Ut = union(0)
cen = Ut.triangles_center
_, dist, tri = trimesh.proximity.closest_point(U0, cen)
print("distance centroïde -> surface repos max", round(float(dist.max()),6), flush=True)
n_rest = U0.face_normals[tri]; n_pose = Ut.face_normals
print("θ=0 plis (témoin, doit être 0):", int((np.einsum("ij,ij->i", n_rest, n_pose) < 0).sum()), "faces", len(Ut.faces), flush=True)
print("normales : même orientation globale ?", float(np.mean(np.einsum('ij,ij->i', n_rest, n_pose))), flush=True)
