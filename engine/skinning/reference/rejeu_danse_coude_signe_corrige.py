import json, numpy as np
exec(open('volume_interpenetration.py').read().split('for Rs in (0.07,):')[0])
ax = -ax  # erreur 110 : signe corrigé (flexion = poignet vers l avant)
import sys
S = '/tmp/claude-0/-home-claude/9ce8e1e5-f7cf-5619-8a75-3c6d9a11ab1c/scratchpad/hiphop/serie.json'
d = json.load(open(S))
angles = [round(x/5)*5 for x in d["coude_droit"]]
from collections import Counter
cnt = Counter(angles)
res = {}
for th in sorted(cnt):
    v, fu, ff = mesure(th, 0.07)
    res[th] = round(float(v), 3) if v is not None else None
    print(f"θ={th}: frames={cnt[th]} interpénétration={res[th]} cm3", flush=True)
tot = sum(cnt[th]*(res[th] or 0) for th in cnt)
n_pen = sum(cnt[th] for th in cnt if (res[th] or 0) > 0)
print("images avec pénétration :", n_pen, "sur", len(angles), "; volume cumulé pondéré :", round(tot,2), flush=True)
json.dump({"theta_frames": cnt, "volume_cm3": res}, open('/home/claude/rejeu_coude_signe_corrige.json','w'), default=str, indent=1)
