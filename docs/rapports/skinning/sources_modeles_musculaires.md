# Sources pour une déformation musculaire ou anatomique : licences et tailles (vérifiées le 2026-11-05)

Aucun téléchargement n'a été fait. Ce document ne fait que recenser les conditions.

| Source | Ce qui est vérifié | Licence | Taille | Statut |
|---|---|---|---|---|
| OpenSim, modèle Rajagopal 2016 (simtk.org/home/full_body) | Fichiers FullBodyModel-4.0.zip et ModelWithSampleSimulations-4.0.zip | « MIT Use Agreement » (texte non reproduit sur la page, à lire dans l'accord) | non indiquée | À vérifier : texte de l'accord, taille |
| SMPL (spec.is.tue.mpg.de) | Licence SPEC lue | Usage commercial interdit ; modification et redistribution interdites sans permission | — | **Exclu** : incompatible avec l'usage du moteur |
| SKEL (arXiv 2509.06607, dépôt MarilynKeller/SKEL) | Non vérifié : la page du dépôt n'a pas pu être lue | inconnue | inconnue | À vérifier, URL à fournir |

Conséquences : aucune donnée n'est téléchargée ; OpenSim exige en plus un moteur de simulation musculaire (Java/C++) dont
le coût CPU et l'intégration restent à mesurer.

## Mise à jour (2026-11-05, vérifié)
- **OpenSim, modèle Rajagopal 2016** : licence MIT (« Copyright (c) 2015, Stanford University »), texte complet dans
  `docs/rapports/skinning/licences/LICENCE_MIT_Rajagopal_OpenSim_full_body.txt`. Source : page projet simtk.org/projects/full_body.
  Usage commercial et modification permis, mention de l'auteur requise, garantie exclue.
- **Archives** : FullBodyModel-4.0.zip (fichier 5525) et ModelWithSampleSimulations-4.0.zip (fichier 5526). Taille non
  disponible : le téléchargement redirige vers une page de connexion SimTK. **Téléchargement non effectué** : aucun
  identifiant n'est géré par la session.
- Le logiciel OpenSim est sous Apache 2.0 (page de licence OpenSim, api_docs 3.1).
- Attendu, non vérifié : le modèle contient des géométries d'os et de muscles, sans peau. Un modèle musculaire ne fournit
  donc pas de forme cible de peau. À confirmer après ouverture de l'archive.
- **SMPL** : seul le résumé de l'article (DOI 10.1145/2816795.2818013) a été lu. Enseignements retenus pour la méthode
  (et non ses données ni son modèle) : corrections dépendantes de la pose, linéaires dans les éléments des matrices de
  rotation ; apprentissage à partir de maillages alignés (donc de données d'entraînement) ; les variantes LBS et DQS sont
  toutes deux utilisées comme base. SMPL reste exclu d'un usage direct (licence).
