exec(open('test_dqs_coude.py').read())
from scipy.spatial.transform import Rotation as Rot
avant_ax = ix["mixamorig:LeftForeArm"]
# avant (+Y) : orteils du pied gauche
avant = np.array(J["mixamorig:LeftFoot"]["queue"]) - np.array(J["mixamorig:LeftFoot"]["tete"])
avant[2] = 0; avant /= np.linalg.norm(avant)
print("sens avant (orteils) :", np.round(avant,3), " axe ax :", np.round(ax,3), flush=True)
poignet_i = ix["mixamorig:LeftHand"]
wrist_rest = h[poignet_i]
dom = np.argmax(W,1)
bras_sup = np.isin(dom, [ix["mixamorig:LeftArm"], ix["mixamorig:LeftArmHelper"]]) & (np.linalg.norm(rest-c,axis=1) > 0.12)
avant_m = np.isin(dom, [avant_ax, ix["mixamorig:LeftHand"]]) & (np.linalg.norm(rest-c,axis=1) > 0.12)
for th in (60, 120):
    P = pose(th)
    # 1) poignet : déplacement vers l'avant (+Y de l'avant)
    dw = np.array(P[np.where(W[:,poignet_i]>0.5)[0]]).mean(0) - np.array(rest[np.where(W[:,poignet_i]>0.5)[0]]).mean(0)
    print(f"θ={th}: déplacement moyen des sommets de la main · avant = {dw @ avant*100:.2f} cm (positif = vers l'avant)", flush=True)
    # 2) bras supérieur loin du coude : doit rester immobile
    dsup = np.linalg.norm(P[bras_sup]-rest[bras_sup],axis=1)
    print(f"θ={th}: bras supérieur (>12 cm du coude) : déplacement max {dsup.max()*1000:.3f} mm", flush=True)
    # 3) torsion : rotation de Kabsch sur les sommets de l'avant-bras loin de la jointure
    X = rest[avant_m]-rest[avant_m].mean(0); Y = P[avant_m]-P[avant_m].mean(0)
    Hm = X.T@Y; U,S,Vt = np.linalg.svd(Hm); Dg = np.diag([1,1,np.sign(np.linalg.det(Vt.T@U.T))])
    Rk = Vt.T@Dg@U.T; rv = Rot.from_matrix(Rk).as_rotvec(); phi = np.linalg.norm(rv); axe = rv/phi
    print(f"θ={th}: avant-bras, rotation ajustée {np.degrees(phi):.2f}°, axe ajusté · ax = {abs(axe@ax):.4f} (1 = flexion pure, aucune torsion)", flush=True)
