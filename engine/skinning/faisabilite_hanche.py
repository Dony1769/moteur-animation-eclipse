import sys, json, numpy as np
sys.argv = [sys.argv[0], sys.argv[1]]
sys.path.insert(0, "/home/claude/moteur_3_0/engine/skinning")
import injectif_hanche as base
import injectif_hanche_v2 as v
from correctif_arap import _rotations
from pathlib import Path
out = []
for Bw in (0.15, 0.25, 0.35):
    s = base.s
    base.bande = np.abs(s) < Bw
    base.proximal = (~base.bande) & (s < 0)
    base.distal = (~base.bande) & (s >= 0)
    base.libre = base.bande
    for A in (1.0, 0.5, 0.25):
        base.A_DISTAL = A
        th = 30.0
        solveur = base.factoriser()
        p = base.t.rest.copy()
        fixe = p.copy()
        fixe[base.proximal] = base.cible_proximale(th)[base.proximal]
        fixe[base.distal] = base.cible_rigide(th)[base.distal]
        am0 = None
        for it in range(80):
            R = _rotations(base.t.rest, p, base.ij, base.N, base.wij)
            pn = base.etape_globale(p, R, fixe, solveur)
            dp = pn - p
            am = v.alpha_max(p, dp)
            if am0 is None: am0 = am
            p = p + min(1.0, 0.8 * am) * dp
        err = float(np.linalg.norm((p - base.cible_rigide(th))[base.distal], axis=1).max())
        row = dict(B=Bw, A_distal=A, alpha_max_premier_pas=round(am0, 4), erreur_distal_80it_m=round(err, 4), inv=base.inversions(p))
        out.append(row); print(row, flush=True)
Path("/tmp/claude-0/-home-claude/9ce8e1e5-f7cf-5619-8a75-3c6d9a11ab1c/scratchpad/faisab.json").write_text(json.dumps(out, indent=2))
print("FIN", flush=True)
