# Mesures : étape A (décor, 1280×540)

- Moteur : Cycles CPU, 16 échantillons, débruitage OpenImageDenoise, 3 rebonds, sans caustiques.
- Temps d'une image : 37,6 s (rendu seul), chargement et construction : 0,1 s (maillages partagés).
- Polygones : falaise namaqualand LOD1 47 184 ; rock_face_01 20 174 ; sable LOD3 92 432 par instance,
  environ 150 instances (≈ 14 M polygones au total, instances liées).
- Estimation pour 15 minutes à 24 images/s (21 600 images) : 37,6 s × 21 600 ≈ 226 h sans simulation de
  poussière. Le budget de la consigne (un plan de 6 s sous une heure) n'est pas respecté à cette qualité :
  il faudra réduire les instances de sable et la résolution avant l'étape C.
- Limites observées : petits trous blancs dans le sol (espacement des instances), ciel encore gris
  (HDRI à faible intensité), pas de poussière, pas de personnage.
