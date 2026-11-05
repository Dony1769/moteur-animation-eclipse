# Articulations et jonctions du squelette (phase 4, révision demandée par l'utilisateur)

## Constat
Le squelette actuel relie les os (cuisse, jambe, bras, avant-bras, main) directement entre eux, et le poids
des sommets est mélangé sur une large zone autour du genou ou du coude. Quand l'articulation tourne, les
sommets de cette zone reçoivent des transformations différentes et le maillage s'aplatit ou rentre dans le
corps (plis mesurés à 105° et 120° sur la jambe, et sur le bras à 120°).

## Principe retenu
1. **Les os-segments sont rigides.** Cuisse, jambe, bras, avant-bras et main sont des bâtons : ils ne se
   déforment jamais, ils se déplacent seulement par leur articulation.
2. **Chaque articulation est une boîte de jonction**, un petit nœud placé au centre anatomique de
   l'articulation. Il porte la zone de sommets de la jointure (genou, coude, poignet, épaule).
   La jonction tourne ; les segments qui la prolongent restent rigides.
3. **Le recouvrement se fait par une calotte**, pas par un mélange de matrices. Autour de la jonction, les
   sommets appartiennent à la calotte rigide du nœud, de rayon suffisant pour couvrir l'écart entre les deux
   segments quand l'articulation se plie. Le mélange de poids ne sert qu'à une bande très mince.
4. **Mouvement anatomique par type d'articulation** :
   - charnière (genou, coude) : un seul axe, flexion 0 à ~140–150°, pas de rotation axiale ;
   - rotule sphérique (épaule, hanche) : trois axes, mais l'épaule et la hanche ne doivent pas traverser le tronc ;
   - condylienne (poignet) : deux axes (flexion/extension et inclinaison radiale/ulnaire) ;
   - cheville : charnière principale, avec une petite marge.

## Articulations à créer (corps HBM)
| Articulation | Os reliés | Type | Centre (source) |
|---|---|---|---|
| Épaule | tronc / humérus | sphérique | centre du chemin mesuré du bras (`placer_articulations`) |
| Coude | humérus / avant-bras | charnière | point mesuré à 0,186 h + 0,146 h (estimation signalée) |
| Poignet | avant-bras / main | condylienne | point mesuré à 0,146 h + 0,108 h (estimation signalée) |
| Hanche | bassin / cuisse | sphérique | à mesurer sur le maillage |
| Genou | cuisse / jambe | charnière | à mesurer sur le maillage |
| Cheville | jambe / pied | charnière | à mesurer sur le maillage |

Les centres sont **estimés** tant qu'ils ne sont pas mesurés sur le maillage. Chaque estimation est signalée
comme telle dans le rapport de validation.

## Validation (critères mesurables)
- 0 pli à 60, 90, 105, 120° (test Blender `valide_base_blender.py`, métrique de pli existante) ;
- étirement maximal ≤ 1,25 sur les poses de test ;
- aucun sommet hors du volume corporel au-delà de la tolérance d'extrapolation ;
- rapport par pose dans `docs/rapports/`.

## Ce qui reste à faire
1. Ajouter les nœuds de jonction au squelette HBM (`engine/rigging/`), en conservant les 47 os existants.
2. Affecter les sommets : segment seul hors de la zone, calotte rigide dans la zone d'articulation.
3. Revalider le genou, le coude et le poignet dans Blender ; comparer avec la base actuelle.
4. Consigner les résultats et les erreurs dans `docs/erreurs_apprises.md`.
