"""Mesure complète de la bande de jonction (erreur 122) : effectif, médiane, p95, p99, fraction > 1,15.
Usage : python3 mesure_bande_complete.py <dossier_donnees>"""
import sys, json, numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_chaine_hanche as t
from articulation_chaine import chaine, deformer

def statistiques(articulation, th, borne=1.15):
    if articulation == "hanche":
        parent = t.ix["mixamorig:Hips"]; enfants = [t.ix["mixamorig:LeftUpLeg"], t.ix["mixamorig:LeftLeg"], t.ix["mixamorig:LeftFoot"]]
        p0 = t.h[t.ix["mixamorig:LeftUpLeg"]]; dirl = t.h[t.ix["mixamorig:LeftLeg"]] - p0
    else:
        parent = t.ix["mixamorig:LeftUpLeg"]; enfants = [t.ix["mixamorig:LeftLeg"], t.ix["mixamorig:LeftFoot"]]
        p0 = t.h[t.ix["mixamorig:LeftLeg"]]; dirl = t.h[t.ix["mixamorig:LeftFoot"]] - p0
    axe = np.cross(dirl / np.linalg.norm(dirl), t.Y); axe /= np.linalg.norm(axe)
    W2, Ms, info = chaine(t.rest, t.dom, parent, enfants, t.M_de(p0, axe, th), t.K, t.B)
    P = deformer(t.rest, W2, Ms)
    e = t.aretes
    L0 = np.linalg.norm(t.rest[e[:, 0]] - t.rest[e[:, 1]], axis=1)
    L1 = np.linalg.norm(P[e[:, 0]] - P[e[:, 1]], axis=1)
    r = L1 / np.maximum(L0, 1e-9)
    mid = (t.rest[e[:, 0]] + t.rest[e[:, 1]]) / 2
    band = np.linalg.norm(mid - info["pivot"], axis=1) < 0.10
    rb = r[band]
    return dict(articulation=articulation, th=th, n_aretes_bande=int(band.sum()),
                mediane=round(float(np.median(rb)), 4), p95=round(float(np.percentile(rb, 95)), 4),
                p99=round(float(np.percentile(rb, 99)), 4), fraction_sup_borne=round(float((rb > borne).mean()), 4),
                borne=borne)

if __name__ == "__main__":
    sorties = []
    for art, angles in (("genou", (60, 90, 105, 120)), ("hanche", (30, 60, 90, 105, 120))):
        for th in angles:
            s = statistiques(art, th); sorties.append(s); print(s, flush=True)
    out = Path(__file__).resolve().parents[2] / "docs" / "rapports" / "phase4_bande_complete.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(sorties, indent=2, ensure_ascii=False))
    print("ECRIT", out, flush=True)
