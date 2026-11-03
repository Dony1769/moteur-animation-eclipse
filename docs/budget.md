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
