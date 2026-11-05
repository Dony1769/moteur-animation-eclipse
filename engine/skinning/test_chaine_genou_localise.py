import sys
exec(open("/tmp/claude-0/-home-claude/9ce8e1e5-f7cf-5619-8a75-3c6d9a11ab1c/scratchpad/articulations/chaine_genou.py").read().split('print("théta')[0])
for B in (0.10, 0.12, 0.15, 0.20):
    for th in (105,120):
        W,Ms=chaine(th,8,B)
        pts=deformer(W,Ms)
        lr=np.linalg.norm(rest[aretes[:,0]]-rest[aretes[:,1]],axis=1)
        lp=np.linalg.norm(pts[aretes[:,0]]-pts[aretes[:,1]],axis=1)
        ok=lr>0; r=np.where(ok,lp/np.where(ok,lr,1),1)
        k=np.argmax(r); v=aretes[k,0]
        pl,e=mesurer(W,Ms)
        print(f"B={B} θ{th}: plis {pl}, max {r.max():.2f}, p99 {np.quantile(r,0.99):.2f}, arête max en z={rest[v,2]:.3f} (genou z={(pose_angle(th)[:3,3]@np.eye(3)[2]):.3f})")
