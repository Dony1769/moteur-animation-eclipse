# Étape 3a : vérification des données de référence avant toute correction

Aucune correction n'est générée avant ce bilan.

## 1. Correspondance des sommets base ↔ HR (HBM masculin, fichier poses2.npz)
- Base : 10 582 sommets ; HR : 677 442 sommets ; bornes identiques à 1e-3 m près (même repère, mètres).
- Pour chaque sommet de base, le plus proche sommet HR est à 1,08e-6 m au maximum (p99 9,8e-7 m) ; 99,3 % sont exacts.
- Les 10 582 sommets de base sont couverts par des sommets HR distincts : correspondance démontrée.
- Féminin (femme.npz) : mêmes données HR, même bilan (5 poses HR).
- Maria : aucune donnée HR. Pas de correspondance démontrable : aucune correction ne peut être calculée à partir des HR pour Maria.

## 2. Repères, unités, transformations
- Masculin et féminin : repère Blender, mètres ; origine des os identique au squelette extrait (étape 1, Hips à −2,264 / −0,034 / 0,873).
- Maria : repère propre ; origine des os identique au squelette extrait (Hips à 0 / −0,018 / 1,052). Échelle d'objet 0,01 dans le FBX,
  appliquée par Blender : longueurs en mètres (cuisse 0,43 m).
- Matrices de pose (`__os`) : 19 os (HBM) et 65 os (Maria), mêmes ordres de noms que les poids.

## 3. Poses réellement disponibles
- 28 poses par personnage (flexions, abductions, rotations, genou, combinaisons) pour HBM masculin, féminin et Maria.
- Poses avec maillage HR : seulement 5 par personnage HBM (L_flex90, L_flex120, L_genou90, R_flex90, L_combo_flex120_genou90).
  Maria : 0.

## 4. Données fiables ou transférées ?
- **Vérité indépendante : aucune.** Les poses HR, évaluées sur les sommets de base, sont identiques à la référence Blender (`ctrl`)
  à 0,0000 m. La référence Blender est elle-même LBS : LBS(projet) − ctrl = 3,8e-7 m (L_flex90, L_genou90, combo) ; DQS − ctrl = 0,03 à 0,07 m.
- Donc les « HR » ne contiennent pas une déformation plus fidèle : ce sont des LBS évalués sur le maillage subdivisé.
- Conséquence : aucune cible corrective (blend shape ou PSD) ne peut être apprise à partir de ces données. Une
  correction doit être justifiée par un modèle (contraintes géométriques, anatomie), et évaluée par les métriques
  d'étirement, de retournement, de volume et d'intersection, pas par comparaison à une vérité.

## 5. Conclusion
- Autorisé : génération procédurale sous contraintes (étape 3b), sans cible externe.
- Interdit : toute affirmation d'une correction « validée contre les HR » ou « apprise sur les poses HR ».
- Maria n'a aucune donnée HR : elle servira uniquement de test de généralisation.
