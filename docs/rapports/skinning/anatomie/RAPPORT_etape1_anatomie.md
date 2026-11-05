# Étape 1 : extraction anatomique réelle (phase 4, correction procédurale)

## Outils et méthode
- Blender 4.5.15 LTS, installation existante (`/home/claude/moteur3d/tools/blender-4.5.15-linux-x64`), liée
  dans `/home/claude/outils/blender-4.5.15` (lien, non versionné). Exécution en mode `-b --factory-startup --disable-autoexec`.
- `engine/anatomie/extraire_squelette.py` : longueurs, parentés, têtes, queues, axes, poids par sommet. Aucune valeur
  de remplacement ; les os terminaux sont marqués `longueur_fiable = false`.
- `engine/anatomie/analyser_topologie.py` : classification par topologie (segments, jonctions) et géométrie (hauteur,
  ordre x), sans les noms. Sortie : jambes (x_min / x_max), tronc, cou, bras, ambiguïtés, représentation.
- `engine/anatomie/test_analyse_topologie.py` : 42 contrôles, 0 échec, 0 sauté (commande :
  `ANATOMIE_SCRATCH=<dossier des .npz> python3 engine/anatomie/test_analyse_topologie.py`).

## Données extraites

| Corps | Fichier source | Os | Os avec poids | Sommets | Hauteur maillage | Cuisse | Jambe | Largeur hanches |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Maria | FBX Mixamo (pièce jointe) | 65 | 52 | 8136 | 1,753 m | 0,4317 m | 0,4082 m | 0,1938 m |
| HBM masculin | corps_final.blend | 21 | 21 | 10582 | 1,690 m | 0,3971 m | 0,4140 m | 0,2200 m |
| HBM féminin | femme_skin.blend (corps féminin) | 19 | 19 | 10582 | 1,639 m | 0,3971 m | 0,4140 m | 0,2200 m |

Remarques vérifiées :
- Le rig de 19 os utilisé jusqu'ici ne correspond pas à Maria : le FBX en contient 65, dont 52 ont des poids.
- Le squelette HBM féminin est identique au masculin (mêmes longueurs). La morphologie féminine vient de la géométrie
  seulement (entrées 167-168).
- Le fichier squelette complet HBM n'a pas de peau : les poids viennent de corps_final.blend.
- Os terminaux : 13 sur Maria, non fiables (entrée 169). Pied masculin/féminin : os terminal, longueur non fiable.

## Classification sans noms (résultat)

| Corps | Jambes | Tronc | Cou | Bras | Ambigus |
|---|---|---|---|---|---:|
| Maria | 2 × 5 os (cuisse, jambe, pied, orteils) | Spine, Spine1, Spine2 | Neck, Head | 2 × 4 | 0 |
| HBM masculin | 2 × 3 os | Spine, Spine1 | Neck, Head | 2 × 4 | 2 (auxiliaires de bras) |
| HBM féminin | 2 × 3 os | Spine, Spine1 | Neck, Head | 2 × 4 | 0 |

Les noms ne servent qu'au contrôle a posteriori (T2) ; le côté gauche/droit reste une convention (entrée 170).

## Os dominants par région (sommets, argmax des poids)

| Région | Maria | HBM masculin | HBM féminin |
|---|---:|---:|---:|
| bassin (racine) | 464 | 37 | 49 |
| jambe x_min | 625 | 1751 | 1755 |
| jambe x_max | 626 | 1757 | 1753 |
| tronc | 1775 | 428 | 496 |
| bras x_min | 1296 | 1354 | 1297 |
| bras x_max | 1254 | 1357 | 1298 |
| cou + tête | 1438 | 3898 | 3934 |
| non classé (doigts, orteils) | 658 | 0 | 0 |

Le total égale le nombre de sommets extraits (test T5). Le cou + tête des HBM descend à 1,28 m, sous la base du cou
(1,33 m) : les poids répartissent la poitrine haute sur le cou (entrée 172). Observé, non corrigé.

## Limites de l'étape 1
- Les longueurs de tronc et de cou ne sont fiables que si chaque os a un enfant ; sur les HBM, le tronc compte 2 os.
- Les épaules ne sont pas représentées comme articulations séparées du tronc dans les HBM (épaule = premier os du bras).
- Aucun maillage HR (MULTIRES) n'est utilisé ici : ce sont les maillages de base (10582 sommets).
- Vérification visuelle : non faite à cette étape (pas de rendu). Rien n'est affirmé visuellement.

## Suite
Étape 2 : correction procédurale adaptée aux longueurs réelles (rapport à venir).
