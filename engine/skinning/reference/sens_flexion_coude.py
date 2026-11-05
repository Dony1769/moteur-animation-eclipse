exec(open('torsion_coude.py').read().split('for th in (60, 120):')[0])
poig_idx = np.where(W[:,poignet_i]>0.5)[0]
for nom, axe_test in (("ax actuel", ax), ("ax inversé", -ax)):
    for th in (30, 60, 120):
        R = np.tile(np.eye(3),(B,1,1)); R[ix["mixamorig:LeftForeArm"]] = Rot.from_rotvec(axe_test*np.radians(th)).as_matrix()
        G, dd = skin_transforms(parent, h, R); P = dqs(rest, W, G, dd)
        dw = (P[poig_idx]-rest[poig_idx]).mean(0)
        print(f"{nom} θ={th}: poignet déplacé vers l'avant de {dw@avant*100:+.2f} cm", flush=True)
