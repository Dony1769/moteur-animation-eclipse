"""Tests de la fusion de vues (texturage maison), sur le maillage de base du générateur (phase 2).

Critères mesurables :
  - une face très orientée vers une vue reçoit la couleur de cette vue (erreur < 0,02) ;
  - une face orientée à l'opposé reçoit la couleur de la vue opposée ;
  - les faces de bord (45°) reçoivent un mélange : leur couleur est entre les deux couleurs de vues ;
  - couverture : fraction des faces sans aucune vue (reportée, pas cachée).
Limite : pas de test d'occlusion (documentée dans fusion_vues.py).
"""
import sys, json
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "human_generator"))
import corps as c
import fusion_vues as fv

V, F = c.charger_base()
F = np.asarray([f for f in F if len(f) >= 3], dtype=int)
Fm = np.asarray([f[:3] for f in F])   # triangles : on prend les 3 premiers sommets (suffisant pour la normale)
N = fv.normales_faces(V, Fm)

fond = 0.5
couleurs = {nom: np.full((len(Fm), 3), fond) for nom in fv.VUES_CANONIQUES}
couleurs["avant"] = np.full((len(Fm), 3), fond + 0.2)     # la vue avant a un éclairage décalé de +0,2

out, couv = fv.fusionner(V, Fm, couleurs)
face_avant = N[:, 2] > 0.9
face_arriere = N[:, 2] < -0.9
bord = (np.abs(N[:, 2]) < 0.75) & (N[:, 2] > 0.5)    # ~40° à 60° de la face avant

err_avant = float(np.abs(out[face_avant, 0] - (fond + 0.2)).mean())
err_arriere = float(np.abs(out[face_arriere, 0] - fond).mean())
mel = out[bord, 0]
ok_melange = bool(np.all((mel >= fond - 1e-6) & (mel <= fond + 0.2 + 1e-6)))
rapport = dict(
    faces=int(len(Fm)),
    faces_avant=int(face_avant.sum()), erreur_moyenne_face_avant=round(err_avant, 5),
    faces_arriere=int(face_arriere.sum()), erreur_moyenne_face_arriere=round(err_arriere, 5),
    faces_bord=int(bord.sum()), melange_entre_vues=ok_melange,
    faces_non_couvertes=int((couv <= 1e-12).sum()),
    statut="VALIDE_TECHNIQUE" if (err_avant < 0.02 and err_arriere < 0.02 and ok_melange) else "ECHEC",
    limite="pas de test d'occlusion : une vue voit aussi les faces cachées (voir fusion_vues.py)")
assert err_avant < 0.02, f"face avant mal colorée : {err_avant}"
assert err_arriere < 0.02, f"face arrière mal colorée : {err_arriere}"
assert ok_melange, "les faces de bord ne sont pas un mélange des deux vues"
out_path = Path(__file__).resolve().parents[2] / "docs" / "rapports" / "texturage_fusion_vues.json"
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(rapport, indent=2, ensure_ascii=False))
print(json.dumps(rapport, indent=2, ensure_ascii=False))
