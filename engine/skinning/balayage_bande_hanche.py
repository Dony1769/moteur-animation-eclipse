"""Balayage de la demi-bande B et du nombre de nœuds K de la chaîne coaxiale (hanche, témoin genou).
Critère complet (erreur 122/123) : n, médiane, p95, p99, fraction > 1,15 dans la bande de 10 cm."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import test_chaine_hanche as t
import mesure_bande_complete as mb

sorties = []
for K in (8, 16):
    for B in (0.15, 0.25):
        t.K = K; t.B = B; mb.t.K = K; mb.t.B = B
        for art, angles in (("genou", (120,)), ("hanche", (90, 120))):
            for th in angles:
                s = mb.statistiques(art, th); s.update(K=K, B=B); sorties.append(s)
                print(s, flush=True)
out = Path(__file__).resolve().parents[2] / "docs" / "rapports" / "phase4_balayage_bande_hanche.json"
out.write_text(json.dumps(sorties, indent=2, ensure_ascii=False))
print("ECRIT", out, flush=True)
