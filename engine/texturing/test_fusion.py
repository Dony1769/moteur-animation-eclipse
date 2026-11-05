"""Tests de la fusion de vues (texturage maison), sur le maillage de base du générateur (phase 2).

Critères mesurables :
  - une face très orientée vers une vue reçoit la couleur de cette vue (erreur < 0,02) ;
  - une face orientée à l'opposé reçoit la couleur de la vue opposée ;
  - les faces de bord (45°) reçoivent un mélange : leur couleur est entre les deux couleurs de vues ;
  - couverture : fraction des faces sans aucune vue (reportée, pas cachée) ;
  - occlusion : une face tournée vers l'avant mais cachée ne reçoit pas la couleur de la vue avant.
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

import visibilite as vis
visibles = {nom: vis.visibilite_rayon(V, Fm, fv.VUES_CANONIQUES[nom]).astype(float) for nom in fv.VUES_CANONIQUES}
out, couv = fv.fusionner(V, Fm, couleurs, visibles=visibles)
# test d'occlusion : faces tournées vers l'avant MAIS cachées dans la vue avant (sans visibilité, elles prendraient +0,2)
cachees_avant = (N[:, 2] > 0.3) & (visibles["avant"] < 0.5)
cachees_couvertes = cachees_avant & (couv > 1e-12)       # vues par une autre vue : elles doivent valoir fond
err_caches = float(np.abs(out[cachees_couvertes, 0] - fond).mean()) if cachees_couvertes.any() else 0.0
face_avant = (N[:, 2] > 0.9) & (visibles["avant"] > 0.5)   # seulement les faces réellement vues de l'avant
face_arriere = (N[:, 2] < -0.9) & (visibles["arriere"] > 0.5)
bord = (np.abs(N[:, 2]) < 0.75) & (N[:, 2] > 0.5)    # ~40° à 60° de la face avant

err_avant = float(np.abs(out[face_avant, 0] - (fond + 0.2)).mean())
err_arriere = float(np.abs(out[face_arriere, 0] - fond).mean())
bord = bord & (couv > 1e-12)                          # faces vues par au moins une vue (les faces internes restent à 0)
mel = out[bord, 0]
ok_melange = bool(np.all((mel >= fond - 1e-6) & (mel <= fond + 0.2 + 1e-6)))
rapport = dict(
    faces=int(len(Fm)),
    faces_avant=int(face_avant.sum()), erreur_moyenne_face_avant=round(err_avant, 5),
    faces_arriere=int(face_arriere.sum()), erreur_moyenne_face_arriere=round(err_arriere, 5),
    faces_tournees_avant_au_total=int((N[:, 2] > 0.9).sum()),
    note_surfaces_internes="environ la moitié des faces tournées vers l'avant sont cachées : surfaces internes du maillage de base (entrée 139)",
    faces_bord=int(bord.sum()), melange_entre_vues=ok_melange,
    faces_non_couvertes=int((couv <= 1e-12).sum()),
    faces_tournees_avant_cachees=int(cachees_avant.sum()), faces_cachees_couvertes=int(cachees_couvertes.sum()),
    erreur_faces_cachees_couvertes=round(err_caches, 5),
    statut="VALIDE_TECHNIQUE" if (err_avant < 0.02 and err_arriere < 0.02 and ok_melange and err_caches < 0.02) else "ECHEC",
    limite="visibilité par lancer de rayon exact ; teintes des vues de test (décalage +0,2 sur la vue avant) seulement")
assert err_avant < 0.02, f"face avant mal colorée : {err_avant}"
assert err_arriere < 0.02, f"face arrière mal colorée : {err_arriere}"
assert ok_melange, "les faces de bord ne sont pas un mélange des deux vues"
assert cachees_couvertes.sum() > 0, "aucune face cachée couverte par une autre vue : test d'occlusion vide"
assert err_caches < 0.02, f"faces cachées colorées par la vue avant : {err_caches}"
out_path = Path(__file__).resolve().parents[2] / "docs" / "rapports" / "texturage_fusion_vues.json"
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(rapport, indent=2, ensure_ascii=False))
print(json.dumps(rapport, indent=2, ensure_ascii=False))
