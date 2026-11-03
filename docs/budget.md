# Budget de calcul

Mesures à décor corrigé (étape 1), débruitage OpenImageDenoise, Cycles CPU.

## Profil « cpu » (benchmark, étape 2)

| Réglage | Temps par image | Qualité à l'œil |
|---|---|---|
| a) 1280×540, 16 ech. | 39,2 s | net, rochers détaillés, un peu de bruit dans les ombres |
| b) 960×405, 8 ech. | 13,0 s | net, détail des rochers conservé |
| c) 640×270, 8 ech. | 6,1 s | lisible, détail réduit |
| d) 640×270, 4 ech. | 4,0 s | bruit visible, détail des rochers faible |

## Planificateur (étape 4) : tests exigés

| Cas | Images | Résultat |
|---|---|---|
| 8 min à 12 i/s, cpu | 5760 | rien ne tient (le plus léger : 640x270 4 ech., 23040 s au total) |
| 8 min à 24 i/s, cpu | 11520 | rien ne tient (le plus léger : 640x270 4 ech., 46080 s au total) |
| 90 s à 24 i/s, cpu | 2160 | rien ne tient (le plus léger : 640x270 4 ech., 8640 s au total) |
| 8 min à 12 i/s, gpu-colab | 5760 | pas de mesure GPU : en attente du notebook Colab (GPU T4) |
| 8 min à 24 i/s, gpu-colab | 11520 | pas de mesure GPU : en attente du notebook Colab (GPU T4) |
| 90 s à 24 i/s, gpu-colab | 2160 | pas de mesure GPU : en attente du notebook Colab (GPU T4) |

## Estimation d'un épisode (étape 9)

Budget : 5400 s (1 h 30). Aucun réglage CPU ne tient, même 640×270 à 4 échantillons (4,0 s/image).
Pour 8 min à 12 i/s (5760 images), il faudrait au plus 0,94 s par image.

## Changement de réglage

Le réglage 1280×540 n'est pas retenu sur CPU : il dépasse le budget. Aucun réglage de remplacement ne le tient non plus.
Le profil gpu-colab reste à mesurer : le notebook Colab doit être lancé par l'utilisateur sur GPU T4.


## Étapes 7 à 9 (3 novembre 2026)

### Étape 7 : combat de 6 s (placeholder Mixamo)
- Personnage : Personnage_Maria.fbx (placeholder), animation Sword_Slash, décor canyon. Scène : scenes/chase_combat.py.
- Réglage 640×270, 4 échantillons, flou de mouvement 0,5. Une seule session Blender pour les 144 images : 600 s, soit 4,2 s par image.
- Secousse de caméra aux impacts (images 30, 78, 126). Poussière et débris : non faits.

### Étape 8 : séquence de 20 s, trois plans
| Plan | Animation | Images | Temps de rendu |
|---|---|---|---|
| A | Idle (attente) | 168 (7 s) | 700 s |
| B | Sword_Slash (combat, étape 7) | 144 (6 s) | 600 s |
| C | Hit_Reaction (impact à l'image 24) | 168 (7 s) | 703 s |
| Total | | 480 (20 s) | environ 2000 s |

Chaque plan est un test sous 20 minutes. Le MP4 assemblé fait 20,00 s, 480 images.

### Étape 9 : estimation d'un épisode (1 h 30 maximum)
Planificateur (budget/plan.py), profils `cpu` et `gpu-colab` :

| Cas | cpu | gpu-colab |
|---|---|---|
| 8 min à 12 i/s | rien ne tient (au mieux 23 040 s à 640×270, 4 échantillons) | rien ne tient (au mieux 30 528 s) |
| 8 min à 24 i/s | rien ne tient (au mieux 46 080 s) | rien ne tient (au mieux 61 056 s) |
| 90 s à 24 i/s | rien ne tient (au mieux 8 640 s) | rien ne tient (au mieux 11 448 s) |

Pourquoi : les mesures `gpu-colab` viennent du notebook, où chaque image relance Blender ; le démarrage pèse donc lourd. Une mesure en un seul processus (comme l'étape 7) n'existe pas encore sur GPU. Il faut un rendu de 96 images en un seul processus sur le T4, puis relancer le planificateur.
Pour un épisode de 8 min à 12 i/s (5 760 images), il faut moins de 0,94 s par image sur la durée totale du budget.
