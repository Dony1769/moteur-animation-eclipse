"""Tests techniques du visage par régions (phase 3, critères mesurables seulement).

  - chaque région a des cibles valides, et les pointeurs LFS sont comptés à part (jamais appliqués) ;
  - une cible valide déplace au moins un sommet, sans NaN ; le nombre de sommets ne change pas ;
  - localité : le recouvrement entre régions (sommets touchés par deux régions) est mesuré et reporté ;
  - un pointeur LFS lève une erreur (pas de silence).

Ces tests ne jugent PAS l'anatomie ni le réalisme : c'est l'inspection visuelle qui le fera, et elle n'est pas faite ici.
Usage : python3 test_visage.py  -> docs/rapports/phase3_visage_regions.json
"""
import sys, json
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import corps as c
import visage as v

V0, F0 = c.charger_base()
rapport = {"regions": {}}
ensembles = {}
for reg in v.REGIONS:
    cibles = v.cibles_region(reg)
    valides = [ch for ch, ok in cibles if ok]
    lfs = [ch for ch, ok in cibles if not ok]
    assert valides, f"aucune cible valide pour {reg}"
    V = V0.copy()
    deplaces = 0
    for ch in valides[:5]:
        Vt = v.appliquer_region(V0, ch, 1.0)
        assert np.isfinite(Vt).all(), ch + " : NaN"
        assert len(Vt) == len(V0)
        deplaces = max(deplaces, int((np.linalg.norm(Vt - V0, axis=1) > 0).sum()))
    assert deplaces > 0, reg + " : aucune cible valide ne déplace de sommet"
    ens = v.sommets_de_region(V0, reg, valides)
    ensembles[reg] = ens
    rapport["regions"][reg] = dict(cibles_valides=len(valides), pointeurs_lfs_ecartes=lfs,
                                    sommets_touches=int(ens.sum()), max_sommets_deplaces_par_cible=deplaces)

# localité : recouvrement entre régions (fraction des sommets touchés par la région A qui le sont aussi par B)
rec = {}
for a in v.REGIONS:
    for b in v.REGIONS:
        if a >= b:
            continue
        inter = int((ensembles[a] & ensembles[b]).sum())
        union = int((ensembles[a] | ensembles[b]).sum())
        rec[f"{a}~{b}"] = round(inter / union, 4) if union else 0.0
rapport["recouvrement_jaccard"] = rec
rapport["recouvrement_max"] = max(rec.values())
rapport["statut"] = "VALIDE_TECHNIQUE"
rapport["note"] = ("Tests techniques seulement : localité mesurée, réalisme non évalué. Une inspection visuelle reste "
                   "obligatoire avant toute validation de phase 3.")
out = Path(__file__).resolve().parents[2] / "docs" / "rapports" / "phase3_visage_regions.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(rapport, indent=2, ensure_ascii=False))
print(json.dumps(rapport, indent=2, ensure_ascii=False)[:2500])
