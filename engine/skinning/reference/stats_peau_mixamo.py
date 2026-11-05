import numpy as np
d = np.load('skin_frames.npz', allow_pickle=True)
V = d['V']; H = d['H']; F = d['faces']; noms = list(d['noms'])
print("taille (m) jambe:", round(float(np.linalg.norm(H[0][noms.index('LeftUpLeg')]-H[0][noms.index('LeftFoot')])),3), flush=True)
iL = {n:i for i,n in enumerate(noms)}
def ang(a,b,c):
    u=a-b; v=c-b
    return np.degrees(np.arccos(np.clip(np.dot(u,v)/np.linalg.norm(u)/np.linalg.norm(v),-1,1)))
e = np.unique(np.sort(np.vstack([F[:,[0,1]],F[:,[1,2]],F[:,[2,0]]]),axis=1),axis=0)
rest = V[0]
L0 = np.linalg.norm(rest[e[:,0]]-rest[e[:,1]],axis=1)
res = {}
for f in range(len(V)):
    h = H[f]
    genou = 180 - ang(h[iL['LeftUpLeg']], h[iL['LeftLeg']], h[iL['LeftFoot']])
    hanche_vert = np.degrees(np.arccos(np.clip(np.dot(h[iL['LeftLeg']]-h[iL['LeftUpLeg']], [0,0,-1])/np.linalg.norm(h[iL['LeftLeg']]-h[iL['LeftUpLeg']]),-1,1)))
    for nom, c in (('genou', h[iL['LeftLeg']]), ('hanche', h[iL['LeftUpLeg']])):
        P = V[f]
        L1 = np.linalg.norm(P[e[:,0]]-P[e[:,1]],axis=1)
        r = L1/np.maximum(L0,1e-9)
        mid = (rest[e[:,0]]+rest[e[:,1]])/2
        band = np.linalg.norm(mid - c, axis=1) < 0.10
        rb = r[band]
        if len(rb)==0: continue
        res.setdefault(nom, []).append(dict(frame=int(d['frames'][f]), flex_genou=round(float(genou),1), cuisse_vert=round(float(hanche_vert),1),
            n=int(band.sum()), mediane=round(float(np.median(rb)),3), p95=round(float(np.percentile(rb,95)),3),
            p99=round(float(np.percentile(rb,99)),3), frac_sup_1_15=round(float((rb>1.15).mean()),3)))
import json
json.dump(res, open('stats_ref.json','w'), indent=1)
for nom in res:
    rows = res[nom]
    print(nom, "n=", rows[0]['n'])
    for row in sorted(rows, key=lambda r: -r['flex_genou'])[:4]:
        print("  ", row)
    mx = max(rows, key=lambda r: r['p95'])
    print("  pire p95:", mx)
