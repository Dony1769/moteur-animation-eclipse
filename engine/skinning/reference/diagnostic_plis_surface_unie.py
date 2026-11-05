exec(open('plis_surface_unie.py').read().split('for th in (30')[0])
Ut = union(30)
cen = Ut.triangles_center
_, dist, tri = trimesh.proximity.closest_point(U0, cen)
plis = np.einsum("ij,ij->i", U0.face_normals[tri], Ut.face_normals) < 0
dc = np.linalg.norm(cen - c, axis=1)
print("plis", int(plis.sum()), "distance au repos des faces signalées (max, cm):", round(float(dist[plis].max())*100,2), "médiane:", round(float(np.median(dist[plis]))*100,2), flush=True)
print("distance au centre des plis (cm) : min", round(float(dc[plis].min())*100,1), "médiane", round(float(np.median(dc[plis]))*100,1), "max", round(float(dc[plis].max())*100,1), flush=True)
print("faces signalées dont la normale posée est presque perpendiculaire au repos (|dot|<0.2) :", int((np.abs(np.einsum("ij,ij->i", U0.face_normals[tri], Ut.face_normals))<0.2)[plis].sum()), flush=True)
print("dot médian des faces signalées :", round(float(np.median(np.einsum("ij,ij->i", U0.face_normals[tri], Ut.face_normals)[plis])),3), flush=True)
