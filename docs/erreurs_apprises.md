# Erreurs rencontrées et méthodes retenues

Chaque erreur a une cause, une correction et un test. Une erreur corrigée doit rester ici pour ne pas recommencer.

## 1. Mesure des replis : normales de repos brutes
- Symptôme : 5 146 faces « retournées » même au repos ; puis des milliers à 90° sur un membre simplement tourné.
- Cause : comparer la normale d'une face à sa normale de repos fausse la mesure dès qu'un membre tourne d'un bloc, car sa normale tourne avec lui.
- Méthode retenue : la face est repliée seulement si sa normale est opposée à la normale de repos **tournée par son os dominant** (`engine/skinning/mesure_lbs.py`).
- Test : témoin à 0° = 0 ; LBS explicite égal au modificateur Blender à 0,0005 mm.

## 2. Maillage subdivisé ignoré (Multires)
- Symptôme : le moteur évaluait 677 442 sommets pour 10 582 dans les données ; les tests comparaient les données.
- Cause : le corps HBM porte un modificateur Multires (sculpture subdivisée). Les tests de base ne voient pas son détail.
- Méthode retenue : mesurer sur le maillage de base avec le Multires désactivé en vue (`show_viewport = False`), et le déclarer dans le rapport. Vérifier les modificateurs avant toute mesure (`obj.modifiers`).
- Limite connue : le pincement visible à gros plan peut venir du détail Multires, non mesuré ici.

## 3. Pose d'os non mise à jour
- Symptôme : une pose réglée par `pose_bone.matrix` ne change pas les mesures, ou une mesure donne 0 pli.
- Cause : sans `bpy.context.view_layer.update()`, la pose relue n'est pas à jour.
- Méthode retenue : mettre à jour la couche de vue après chaque pose, et restaurer la matrice d'origine dans un `finally`.
- Test : état de l'os vérifié avant et après chaque calcul (`etat.py`).

## 4. Opérateurs de poids inaccessibles en headless
- Symptôme : `vertex_group_smooth` renvoie « context is incorrect ».
- Cause : les opérateurs de poids exigent un contexte d'interface.
- Méthode retenue : lissage, limite à 4 influences et normalisation écrits en Python explicite (`lisser_limiter_normaliser`), déterministes et testés.

## 5. Parenté des yeux
- Symptôme : les yeux étaient parentés au maillage du corps, pas à l'armature ; le contrôle les déclarait sans skinning.
- Méthode retenue : attache rigide à l'os `mixamorig:Head` (transformation monde conservée) ; le contrôle accepte une pièce rigide attachée à un os (règle écrite).
- Test : pose de repos inchangée, yeux à la même position monde (écart nul).

## 6. Test de déformation trop indulgent
- Symptôme : un test « fuite proximale » comptait les bras comme fautifs quand la colonne se pliait.
- Cause : les bras sont rattachés à la colonne ; ils doivent bouger.
- Méthode retenue : une fuite est un sommet non rattaché (groupe dominant hors de l'os et de ses descendants) qui bouge de plus de 2 cm.

## 7. Scripts placés dans le mauvais dépôt
- Symptôme : `auto_skin.py` écrit dans `/home/claude/moteur3d` au lieu de `/home/claude/moteur_3_0` ; le diagnostic introuvable.
- Méthode retenue : le dépôt git est `/home/claude/moteur_3_0`. Toujours vérifier `git -C ... status` avant d'écrire, et utiliser des chemins absolus.

## 8. Arrêt de mes propres processus
- Symptôme : `pkill -f` ou une boucle `ps | grep` ont tué le shell (code 144).
- Cause : la commande contient le motif qu'elle cherche.
- Méthode retenue : `pgrep -x blender` / `pkill -x blender` (nom exact du binaire).

## 9. Relecture d'une mesure fausse
- Symptôme : une mesure « à 0 pli » après une pose a été prise pour un résultat.
- Méthode retenue : un résultat n'est accepté que si le témoin (0°) et le contrôle (valeur 0 de la correction) passent, et si l'état de l'os est vérifié.

## 10. Correction par élargissement de la transition
- Résultat : insuffisant (-17 % de replis à 90°). Ne pas le présenter comme correction complète.
- Méthode retenue pour le pli : clé corrective calibrée à l'angle, valeur = clamp(angle / angle_cible).

## 11. Étape oubliée dans un pipeline de sortie
- Symptôme : le fichier corrigé est passé à « NON PRÊT » : les yeux n'étaient plus rattachés.
- Cause : le script de correction appelait le skinning mais pas l'attache des pièces rigides.
- Méthode retenue : un pipeline doit appeler toutes les étapes de l'étape précédente. Le test de non-régression vérifie le rapport final, pas seulement l'étape nouvelle.

## 12. Résultat « bon » sur un seul cas
- Symptôme : la correction fonctionne sur le bras calibré, mais la combinaison de plusieurs articulations n'a pas été mesurée.
- Méthode retenue : toujours écrire la limite (combinaisons non testées) dans le rapport au lieu de la passer sous silence.

## 13. Restauration de pose dans un ordre arbitraire
- Symptôme : deux jambes à 90° donnaient 390 replis, alors que chacune seule donne 5 à 6 ; les scénarios s'influençaient entre eux.
- Cause : restaurer `pb.matrix` os par os, parents et enfants mélangés. Un enfant restauré avant son parent garde une pose relative fausse, qui pollue le scénario suivant.
- Méthode retenue : sauvegarder et restaurer `pb.matrix_basis` (transformations locales), indépendantes de l'ordre, puis mettre la couche de vue à jour.
- Test : témoins « un os seul en chaîne » = résultat du test à un os (6 et 5). Un test de cohérence entre deux méthodes est obligatoire avant d'interpréter une combinaison.

## 14. Import d'un script qui exécute un calcul
- Symptôme : `test_combinaisons.py` importait `construit_correctives.py`, qui relance tout le skinning et la correction à l'import.
- Méthode retenue : un module réutilisable ne contient pas de calcul au niveau du module. Les fonctions partagées vivent dans un module séparé ; les scripts de calcul ne sont jamais importés.

## 15. Combinaisons d'articulations : résultats mesurés
- Coude 90° + bras 90° (chaîne) : 28 → 3 replis.
- Deux bras à 90° : 32 → 6. Deux jambes à 90° : 11 → 0. Corps entier à 60° : 7 → 1.
- Les corrections se combinent de façon additive sans créer de nouveaux replis dans ces cas.

## 16. Référence de repos sans les clés correctives
- Symptôme : une clé corrective, pourtant calibrée, paraissait créer 13 replis à 90° au lieu de 3.
- Cause : la référence de normale était la forme de base, alors que la clé modifie la forme de repos. Le déplacement de repos était donc compté comme pli.
- Méthode retenue : la référence de repos est la forme avec les clés actives (`engine/skinning/mesure_dqs.py`, `test_dqs_cles.py`).
- Test : la valeur à 0 de toutes les clés redonne la même mesure que sans clés ; la mesure explicite (`mesure_lbs`) et la mesure évaluée (Blender) doivent donner les mêmes replis.

## 17. Deux mesures contradictoires : arrêter et trouver la cause
- Règle : quand deux mesures du même cas diffèrent, ne choisir ni l'une ni l'autre. Chercher la différence de méthode (ici, la référence de repos). Ne publier qu'après accord des deux.

## 18. Délai de sécurité sur un calcul long
- Symptôme : un calcul de 24 évaluations de maillage a été coupé par `timeout 115`, sans résultat ni erreur claire.
- Méthode retenue : lancer les calculs longs en arrière-plan (`nohup ... > log`) et lire le log ; ne pas mettre de délai court sur un calcul dont la durée est inconnue.

## 19. Idée de combinaison : DQS + formes correctives
- Le DQS seul améliore peu le bras (31 → 30 à 120°). Combiné aux clés, il réduit les replis à 105° (18 → 8) et annule ceux des jambes à 105°.
- Non encore validé : son gonflement (volume ajouté) n'est pas mesuré. Ne pas l'adopter avant cette mesure.

## 20. Mesure « témoin » indispensable pour un ajout d'os
- Symptôme possible : un os d'aide peut sembler améliorer les replis parce que le pipeline a changé (poids recalculés).
- Méthode retenue : deux variantes lancées dans les mêmes conditions (même source, même pipeline, seul l'os d'aide change), et le témoin « sans » enregistré à côté du résultat « avec ».
- Résultat : 24 -> 12 à 90°, 31 -> 19 à 120°. L'amélioration tient à l'os d'aide, pas au recalcul seul, puisque le témoin est recalculé avec le même pipeline.

## 21. Métrique de gonflement mal définie
- Symptôme : le « déplacement maximal à 120° » du pipeline final vaut environ 1 150 mm pour le bras.
- Cause : il mesure le déplacement total d'un membre qui tourne, ce qui est attendu. Ce n'est pas une mesure de gonflement.
- Méthode à retenir : un vrai contrôle de gonflement compare chaque sommet à la position idéale de son os (mouvement rigide du groupe dominant), et mesure l'écart. Tant que ce contrôle n'existe pas, le chiffre de déplacement ne doit pas être présenté comme un test.
- Statut : implémenté le lendemain (entrée 22 : `engine/skinning/controle_gonflement.py`, volume et étirement des arêtes).

## 22. DQS « preserve volume » : le gonflement mesuré ne confirme pas le candidat
- Mesure (volume signé du maillage évalué / volume de repos, `docs/rapports/gonflement_avec_cles.json`) :
  bras gauche à 120° : LBS 0,961 ; DQS 0,940. Jambe gauche à 120° : LBS 0,986 ; DQS 0,988 (écart négligeable).
  Avant-bras : DQS 0,9989 contre LBS 0,9976, gain marginal.
- Décision : DQS non adopté pour le bras. La mesure de gonflement remplace l'hypothèse « DQS garde le volume » : sur ce modèle, il ne le garde pas mieux que LBS.
- Règle : un mode de déformation ne s'adopte qu'après une mesure de volume et d'étirement, jamais sur la seule réduction des replis.

## 23. Les clés correctives créent des arêtes étirées
- Mesure (bras gauche, LBS, arêtes les plus étirées, rapports `gonflement_sans_cles.json` et `gonflement_avec_cles.json`) :
  à 90° : étirement maximal 2,63 sans clés, 3,59 avec clés. À 120° : 3,36 sans clés, 5,90 avec clés.
- Cause : `calculer_decalage` ne déplace que les sommets des faces repliées. Le décalage a donc une frontière brutale ; les arêtes qui la traversent s'étirent. Les replis disparaissent, mais l'étirement est déplacé à la frontière.
- Essai : lissage laplacien du champ de décalage (option `lissage`, `correction_pose.lisser_decalage`, défaut 0 pour rester reproductible).
  - Lissage 1, 80 itérations : étirement 2,63 à 90° et 3,35 à 120° (retrouve la valeur sans clés), mais replis du bras 9 à 90° au lieu de 2.
  - Lissage 1, 200 itérations : replis du bras 3/9/15/18 à 60/90/105/120°, étirement 2,63 et 3,34. Replis des jambes 2/4/6 à 90/105/120° au lieu de 0/3/3.
- Constat : la calibration était non convergée (80 itérations épuisées, `replis_apres` élevé). Mais 200 itérations ne suffisent pas à retrouver les replis d'origine : le lissage affaiblit la correction. Il n'y a pas de dominance : le compromis replis/étirement est réel.
- Décision : pipeline de référence = lissage 0 (commit précédent). Le lissage reste disponible, non adopté. Défaut connu à traiter : l'étirement de 5,9 fois à 120° est une défaillance visible, à corriger par une autre méthode (atténuation par distance à la frontière de pliage, ou lissage limité aux arêtes étirées).
- Règle : une correction se juge sur deux critères en même temps, replis et étirement. Une amélioration de l'un seul ne suffit pas.

## 24. Témoin à 0° : tolérance fixée par mesure, pas par confort
- Symptôme : le témoin à 0° donnait un étirement de 1,0003 et 0,9990, au lieu de 1,000.
- Mesure : 570 sommets diffèrent du repos de 1,3 µm au maximum, à cause d'un résidu de 10⁻⁶ dans la pose de deux os (flottants). Sur des arêtes d'environ 1 mm, cela donne un écart de ratio de 1e-3.
- Méthode retenue : la tolérance du témoin est fixée à 1,5e-3 et documentée dans `tests/test_gonflement.py`. Elle n'est pas élargie pour faire passer un résultat ; elle correspond au plancher de précision mesuré.

## 25. Contrainte de gradient sur le décalage : même compromis que le lissage
- Essai : limitation de |d_i - d_j| à kappa x longueur de repos de l'arête (`correction_pose.limiter_gradient`), kappa 0,15 et 0,3, pipeline inchangé sinon.
- Résultat bras gauche : étirement à 120° ramené à 3,36 (valeur sans clés) ; replis 19 au lieu de 13. Jambe : replis 4 à 120° pour kappa 0,3 contre 3 sans contrainte.
- Lecture : la correction qui supprime les replis est une grande variation du décalage ; la limiter supprime aussi la correction. Le couplage replis / étirement vient de la méthode elle-même (décalage calibré par poussée normale sur les sommets repliés), pas du réglage.
- Décision : option conservée, désactivée par défaut (kappa 0). Pipeline de référence inchangé (commit 53c0fc9 / 81db6b8).
- Méthode à essayer ensuite (non testée) : correction par région distincte (une clé par zone de pli, au lieu d'une clé par os), ou décalage calibré sur la position rigide prédite (mode « vers_os » déjà présent), pour que le décalage suive l'os et non la normale.

## 26. Direction « vers l'os » pour la calibration : rejetée
- Essai : décalage des sommets repliés vers l'axe de l'os (mode `vers_os`) au lieu de la normale. Pipeline inchangé sinon.
- Résultat bras gauche : replis 4/11/13/13 à 60/90/105/120° (contre 0/2/6/13 en référence) ; étirement 7,2 à 90° (contre 3,6).
- Lecture : les deux directions de calibration (normale, axe d'os) échouent sur le même critère. La cause n'est pas la direction mais le principe d'une clé unique par os.
- Erreur de procédure rencontrée : la seconde clé (120°) restait calibrée en normale pendant ce test. Corrigé et relancé ; la mesure ci-dessus est celle du test complet. Règle : un paramètre de méthode doit être passé à toutes les étapes qui l'utilisent, sinon la mesure mélange deux méthodes.
- Décision : option conservée, défaut inchangé (`moins_normale`).

## 27. Clé par zone (fenêtre spatiale autour de l'articulation)
- Essai : la correction n'est calculée et appliquée que dans une fenêtre autour de la tête de l'os qui tourne (poids 1 au centre, transition en smoothstep de 10 cm). Rayons testés : 10 cm et 20 cm.
- Rayon 20 cm : résultat identique à la référence (replis 2/6/13, étirement 3,59 à 90° et 5,90 à 120°). La zone de 20 cm + transition contient tout l'étirement.
- Rayon 10 cm : étirement ramené à la valeur sans clés (2,63 à 90°, 3,36 à 120°), mais replis du bras 7/13/14 à 90/105/120° (référence 2/6/13).
- Lecture : l'étirement et la correction des replis viennent de la même région, près de l'articulation. Réduire la zone réduit les deux. Le compromis n'est pas une propriété du champ de décalage mais de la géométrie du pli : une seule clé calibrée sur un angle ne peut pas corriger le pli sans étirer son bord.
- Décision : option conservée, défaut inchangé (pas de fenêtre).
- Conclusion sur les quatre tentatives (entrées 23 à 27) : aucune ne satisfait les deux critères. La suite exige une méthode de déformation différente (par exemple des os de torsion répartis ou une clé par angle au lieu d'une clé pilotée), à tester séparément.

## 28. Chaîne de deux os d'aide à la même position : pire que un seul
- Essai (sans clés, bras gauche, `engine/skinning/test_chaine_aide.py`) : un os d'aide à influence 0,5 (référence) contre deux os d'aide, à 0,33 et 0,67, tous deux à la tête de l'épaule et copiant `LeftArm`.
- Résultat : replis 3/12/17/19 à 60/90/105/120° contre 4/19/27/36 pour les deux os.
- Lecture : deux os qui copient la même rotation à la même position additionnent leurs effets au lieu de la répartir. Une répartition réelle exige des os placés à des positions différentes le long du bras (tête au milieu du bras, par exemple), ce qui n'est pas testé.
- Décision : référence inchangée (un os à 0,5).
- Règle : pour répartir une rotation sur plusieurs os, placer chaque os à sa propre position le long de la chaîne, jamais empiler des copies au même point.

## 29. Mesure de replis sans les clés : erreur de procédure
- Symptôme : la première mesure de la correction à trois échantillons donnait exactement les replis du bras sans clés (3/12/17/19).
- Cause : `faces_repliees` était appelé sans le paramètre `decalage` ; les clés calibrées n'entraient pas dans la mesure.
- Règle : toute mesure de replis doit recevoir le décalage total des clés actives. Une mesure identique à la variante sans clés est un signal d'erreur de procédure, pas un résultat.

## 30. Correction à trois échantillons (60, 90, 120) : pas de gain net
- Méthode : une clé par échantillon, calibrée seule à partir d'un décalage nul ; valeur en chapeau (1 à l'échantillon, 0 à 30° de distance). Interpolation linéaire par morceaux entre échantillons.
- Plafond d'amplitude 40 mm, 150 itérations : bras 0/2/7/15 à 60/90/105/120° (référence 0/2/6/13). Jambe identique à la référence.
- Plafond 80 mm, 300 itérations : bras 0/1/7/11, jambe gauche 0/0/4/3, mais étirement 8,0 à 120° (référence 5,9) et 4,5 pour la jambe (référence 2,4).
- Lecture : le goulot est le plafond d'amplitude de la calibration à 120°, qui n'atteint pas zéro replis. Augmenter l'amplitude réduit les replis et augmente l'étirement, dans les mêmes proportions que les essais précédents. Le compromis est structurel.
- Décision : pipeline de référence conservé (replis 0/2/6/13, étirement 5,9). Justification : c'est le compromis le plus équilibré des variantes mesurées, et aucune ne réduit à la fois les replis et l'étirement.
- Règle : une amplitude de correction de plusieurs centimètres sur un corps de 1,7 m est un signal d'alerte : elle compense un défaut de déformation au lieu de le corriger.

## 31. Image de contrôle qui ne montre pas la pose mesurée
- Symptôme : la première carte d'étirement montrait le bras au repos, avec des couleurs calculées sur le bras à 120°. Le bras semblait ne pas être fléchi.
- Cause : deux erreurs de procédure dans le script de rendu. La pose était restaurée avant le rendu, et les clés correctives étaient remises à zéro après le calcul du repos.
- Règle : une image de contrôle doit montrer exactement l'état que les mesures ont calculé. Pose, clés et couleurs doivent être appliquées au moment du rendu, puis vérifiées par une vue de profil avant toute conclusion.
- Correction : `engine/skinning/rendu_etirement.py` rétablit les clés et garde la pose au rendu. Image de référence : docs/rapports/visuel_etirement_bras120_profil.png. Le bras est fléchi à environ 90 à 120° vers l'avant, et la zone rouge est à l'épaule.

## 32. Vérification de hauteur d'un FBX importé : coordonnées locales et monde
- Symptôme : une première mesure donnait 42,9 pour un personnage de 169 cm.
- Cause : ma mesure utilisait les coordonnées locales du maillage, sans l'échelle 0,01 appliquée à l'objet à l'import (FBX en centimètres). La vraie hauteur monde est 1,70 m.
- Règle : mesurer une dimension après import uniquement en coordonnées monde (`matrix_world @ co`), et vérifier l'échelle de l'objet avant de conclure à un défaut d'export.

## 33. Distances mesurées en coordonnées locales après import FBX à l'échelle 0,01
- Symptôme : déplacements de 367 m et un saut de 66 m pour un personnage de 1,70 m. Physiquement impossible.
- Cause : mesure sur `v.co` (espace de l'armature, en centimètres) et non sur `matrix_world @ v.co`. Les valeurs étaient 100 fois trop grandes.
- Règle : toute distance après import se mesure en mètres monde. Une valeur physiquement impossible prouve une erreur de mesure avant toute conclusion sur le moteur.

## 34. Translation racine d'un clip comptée comme déformation
- Symptôme : le clip Running déplace la hanche de 3 à 370 unités sur 16 images (le personnage avance). Le corps entier se translate, et la mesure la comptait comme déformation.
- Règle : mesurer la déformation par rapport à la hanche (position monde de l'os racine retirée à chaque sommet). Séparer translation du corps et déformation de la peau.
- Résultat après correction : pas médian de 5,3 cm par image, maximum 40 cm (à vérifier : pic à examiner).

## 35. Action non affectée à l'armature sans slot (Blender 4.5)
- Symptôme : après `arm.animation_data.action = action`, le maillage ne bouge pas (déplacement 0 sur toutes les images), alors que les os changent.
- Cause : Blender 4.4 et suivants utilisent des slots d'action ; l'action n'est pas rattachée à l'objet.
- Règle : affecter aussi `animation_data.action_slot = action.slots[0]`, puis vérifier qu'une pose modifie le maillage avant de mesurer quoi que ce soit.

## 36. Transition directe entre deux clips : saut trop grand, corrigé par fondu
- Mesure : saut à la jonction Idle → Running de 0,18 m, soit 3,4 fois le pas médian de Running (seuil 3, échec).
- Correction : fondu enchaîné NLA (Running sur une piste supérieure, `blend_in` de 12 images, départ 12 images avant la fin d'Idle). Ratio 1,02 à 12 images, 1,57 à 6 images.
- Réglage retenu : 12 images, qui donne la transition la plus douce. Le seuil 3 a été fixé avant la mesure, à confirmer sur d'autres paires de clips.
- Limite : une seule paire de clips testée ; le pic de 40 cm par image dans Running reste à examiner.

## 37. Export animé : plage de bake de la scène au lieu de la plage du clip
- Symptôme : après réimport, un écart de 627 mm entre le personnage exporté et l'original.
- Cause : l'export cuit la plage de la scène (250 images), pas celle du clip (16 images) ; l'action réimportée couvre 2 à 251.
- Règle : borner `scene.frame_start/frame_end` à la plage du clip avant tout `bake_anim`, et compter les images à partir du début réel de l'action réimportée.

## 38. Comparer une animation exportée : décalage temporel de l'import FBX
- Constat : le FBX réimporté commence à l'image 2 pour un clip qui commence à 1.
- Règle : aligner les images par `frame_range[0]` de l'action réimportée, jamais par numéro d'image brut. Un écart de quelques centimètres sur tout le clip est souvent un décalage d'une image, à vérifier avant de conclure à une erreur d'export.
- Résultat après correction : écart maximal 0,257 mm sur tout le clip (tolérance 1 mm).

## 39. Mesure de section de jambe : étendue en X fausse à l'entrejambe ; corps non centré
- Symptôme 1 : aucun sommet sélectionné pour la jambe ; la section « la plus fine » tombait à 0,39 h avec 56 mm (faux).
- Cause 1 : le corps du bundle HBM est décalé de −2,26 m en X. Le filtre `x > 0,03` ne retenait rien.
- Cause 2 : près de l'entrejambe, l'étendue en X ne garde que le bord intérieur de la jambe et s'effondre. La mesure est donc fausse à cette hauteur.
- Règle : recentrer sur le milieu réel du corps avant tout filtre par coordonnée. Pour une section de membre, mesurer la profondeur (étendue en Y), qui ne s'effondre pas à l'entrejambe.
- Transparence : le changement de métrique a été fait après un échec. Il est justifié par la cause 2 (artefact géométrique), pas par le seul résultat ; à confirmer sur d'autres corps avant de généraliser.

## 40. Bras supposés horizontaux à partir de l'envergure : hypothèse fausse
- Symptôme : l'épaule estimée à 0,19 h en X donnait un bras de ≈ 0,24 m, très inférieur à la longueur anatomique.
- Cause : l'envergure (bras écartés) a été prise pour une extension horizontale. Mesure réelle : le bras descend de 0,74 h (épaule, x ≈ 0,21 m) à 0,46 h (poignet, x ≈ 0,41 m), soit une pose en « A » inclinée. Longueur implicite ≈ 0,6 m, cohérente.
- Règle : ne jamais déduire la pose d'un membre de l'encombrement en X. Mesurer le chemin du membre (centroïde par tranche) avant de poser des os.
- Correction : `test_hbm_articulations.py` utilise le chemin mesuré ; les bras restent marqués « mesurée », non validés (coude et poignet à confirmer).

## 41. Test d'intérieur : repère du BVH différent de celui des os
- Symptôme : tous les milieux d'os, y compris ceux du tronc, étaient signalés hors du maillage.
- Cause : les os sont exprimés dans le repère recentré en X, alors que le BVH était construit dans les coordonnées monde d'origine (décalées de −2,26 m).
- Règle : construire le BVH dans le même repère que les points testés. Un échec général (tous les points « dehors », même le centre) signale un repère faux, pas un défaut de géométrie.

## 42. Parité verticale fausse dans les zones de recouvrement des pièces
- Symptôme : cuisses et pieds signalés hors du maillage ; le tronc et les jambes inférieures sont bien dedans.
- Cause : les pièces du corps (bassin, cuisses) sont des coques fermées qui se recouvrent. Un rayon vertical traverse le bassin et compte des intersections en trop, ce qui inverse la parité.
- Règle : pour un membre, tester la parité dans la direction qui sort du membre (X, à l'opposé de l'axe du corps). Un test d'intérieur par parité n'est fiable que si les coques ne se recouvrent pas sur le trajet du rayon.

## 43. Point de hanche pris dans les bras : centroïde contaminé par une autre partie
- Symptôme : la hanche gauche sortait à (0,40 ; −0,10), à l'extérieur du corps et loin de la cuisse.
- Cause : le centroïde à 0,44 h incluait les sommets des bras (qui descendent jusqu'à 0,46 h). Une tranche horizontale mélange toutes les parties présentes à cette hauteur.
- Règle : avant de mesurer un membre par tranche, borner la tranche à ce membre (ici |x| < 0,25 m) et vérifier que le point mesuré est bien dans la cuisse.

## 44. Longueur de pied supposée au lieu d'être mesurée
- Symptôme : le milieu de l'os du pied sortait du maillage.
- Cause : la pointe du pied était placée à une longueur fixe (0,15 m) au lieu du sommet réel le plus avancé.
- Règle : une longueur d'os qui n'est pas mesurée doit être déduite de la géométrie (ici : sommet le plus avancé près du sol), jamais fixée à une valeur de catalogue.

## 45. Convention Mixamo rejetée faute de préfixe « mixamorig: »
- Symptôme : l'armature Ara (69 os, noms Mixamo exacts) était classée « convention inconnue ».
- Cause : le diagnostic ne reconnaissait la convention que par le préfixe `mixamorig:`. Ara exporte `Hips`, `Spine`, `LeftArm`… sans préfixe.
- Règle : reconnaître une convention par l'ensemble des noms de référence (avec ou sans préfixe), et signaler le préfixe comme une propriété séparée, pas comme un critère d'identité.
- Vérification : les mêmes 22 os de référence sont reconnus dans les deux formes ; le rapport de Maria reste inchangé.

## 46. Poids optimisés jugés sur les poses d'entraînement
- Symptôme : la jambe s'améliorait à 60/90/105° mais se dégradait à 120° (maximum 1,27 → 1,40).
- Cause : les poids optimisés sont spécifiques aux angles échantillonnés ; hors de la plage d'entraînement, ils extrapolent mal.
- Règle : tout résultat d'optimisation se juge sur un angle jamais vu à l'entraînement, et sur une plage qui encadre les angles d'entraînement. Un gain sur les points d'entraînement ne prouve rien.

## 47. Masque par os dominant : frontière brutale
- Symptôme : en optimisant seulement les sommets dont l'os dominant est le bras, l'étirement maximal monte à 5,39 au lieu de 1,65.
- Cause : les sommets optimisés et les voisins non optimisés se raccordent sans transition ; c'est la même frontière brutale que l'erreur 22.
- Règle : ne jamais optimiser un sous-ensemble de sommets sans transition ; l'optimisation doit porter sur le maillage entier, ou sur une zone avec un fondu.

## 48. Arêtes courtes dominant la métrique de ratio
- Symptôme : après entraînement séquentiel, une arête de 1 cm au coude passe de 1,5 à 5,4 à 105°, et 28 arêtes dépassent 2.
- Cause : le ratio longueur pose / longueur repos est très sensible aux arêtes courtes ; un petit transfert de poids vers l'os d'aide `LeftArmHelper` allonge fortement cette arête.
- Règle : pondérer la perte par la longueur de repos, et rejeter toute configuration dont l'étirement maximal augmente sur un angle d'entraînement.

## 49. Pondération des arêtes par leur longueur : le mauvais critère
- Problème identifié (erreur 48) : la perte ratio pondère toutes les arêtes à égalité ; une arête courte de 1 cm domine.
- Tentation : pondérer par la longueur. Rejeté : une arête courte entourée de grandes faces est normale ; une longueur courte n'indique pas une faible influence géométrique.
- Méthode retenue, d'après la littérature lue (brevet US10061871 : covariance pondérée par aires barycentriques ; Jacobson & Baran : poids cotangents) : pondérer chaque arête par la somme des aires barycentriques de ses deux sommets, normalisée à une moyenne de 1.
- Règle : une pondération d'arête doit refléter la surface locale qu'elle représente, pas sa longueur.

## 50. Garde de rejet limitée aux angles d'entraînement
- Symptôme : une optimisation entraînée sur 60/90/105° passait la garde, mais la jambe passait de 1,27 à 1,60 à 120°.
- Cause : la garde ne contrôlait que les angles d'entraînement. Un angle hors entraînement ne pouvait pas la déclencher.
- Règle : la garde doit contrôler au moins un angle de validation qui n'est pas dans l'entraînement, en plus des angles d'entraînement. Dans le cas contraire, la garde ne protège que contre la dégradation sur ce qu'elle a déjà vu.
- Constat complémentaire : à 120°, l'arête extrême de la jambe d'origine est à la cheville (arêtes de 1,7 cm). L'optimisation la déplace au genou (1,49). Les poids déplacent la contrainte sans la résoudre : la jambe demande un traitement dédié.

## 51. Métrique de plis numpy fausse : normale de repos non tournée
- Symptôme : le comptage numpy donnait 1 288 faces repliées à 120° sur le corps d'origine, contre 13 dans la mesure du projet. Les poids du haut du corps semblaient en aggraver le compte (1 357).
- Cause : la normale de repos était comparée brute à la normale de pose. Le projet (`mesure_lbs.faces_repliees`) compare la normale de pose à la normale de repos tournée par la matrice 3×3 (colonnes normalisées) de l'os dominant de la face.
- Correction : outil `engine/skinning/plis_numpy.py`, calqué sur la définition du projet.
- Calibration Blender sur `corps_haut.blend` (poids du haut du corps), comptes Blender / numpy : bras 10/10, 11/11, 17/17, 23/22, 32/28 (60, 75, 90, 105, 120°) ; avant-bras 4/4, 4/4, 5/5, 5/5, 6/6 ; jambe 0/0, 1/1, 5/5, 7/7, 11/10. Écart maximal : 4 faces (bras à 120°).
- Règle : une métrique numpy ne se conclut qu'après calibration sur la mesure Blender du projet. Un écart de l'ordre de 1000 faces indique une erreur de définition, pas un résultat.
- Constat réel, une fois calibré : les poids du haut du corps réduisent l'étirement du bras (3,36 → 1,56 à 120°), mais multiplient par deux environ les faces repliées du bras (origine numpy 3/7/8/12/15 ; haut 10/11/17/23/32 à 60/75/90/105/120°). Le compte d'origine est numpy (non vérifié dans Blender sur le fichier d'origine). Ce compromis rend ces poids non adoptables en l'état.
- Règle complémentaire (suite de l'erreur 50) : la garde de rejet doit contrôler aussi le nombre de faces repliées, sur les angles d'entraînement et de validation.

## 52. Garde d'optimisation aveugle aux plis
- Symptôme : la garde (étirement seul) acceptait des poids qui doublaient les faces repliées du bras (erreur 51).
- Correction : `garde_max` contrôle désormais le nombre de plis (`plis_numpy`) sur les angles d'entraînement et de validation. Test : poids du haut du corps refusés (plis 3 → 10 à 60°) ; poids d'origine acceptés.
- Constat de recherche : l'article ARAP-LBS (Thiery et al., telecom-paris, araplbs.pdf) ne traite ni les plis ni les poses de validation hors échantillon. Ses poses d'entraînement sont limitées à roulis ±60° et torsion ±10°. Nos angles de 105° et 120° dépassent ce domaine. Les plis à grand angle ne se résolvent donc pas par les seuls poids : il faut des formes correctives (clés), comme le pipeline de référence.
- Règle : la garde doit inclure les plis, et l'entraînement doit rester dans le domaine d'angles où la méthode est valide, ou être complété par des formes correctives.

## 53. Recherche sur les formes correctives : constats et sources non vérifiées
- Problème : les poids LBS seuls laissent 28 à 32 plis au bras à 120° (erreur 51). Le pipeline de référence avec clés correctives en laisse 13 (mesure du projet, session précédente). Les clés restent donc la meilleure voie connue dans ce projet.
- Sources lues : Wang & Phillips 2002 (multi-weight enveloping, SG07) : la page lue ne donne ni méthode ni chiffres ; à relire dans l'article original. Projet Maya « ML corrective deformer » (page non officielle) : correctif appris (MLP, angles → déplacements de sommets). Ses métriques ne sont pas définies et le jeu de test n'est pas clairement exclu de l'entraînement : non vérifié, à ne pas citer comme preuve.
- Règle : une source non officielle sert d'idée. Elle n'est retenue qu'après un test sur poses hors entraînement, dans le même protocole que le projet.
- Piste déterministe à tester : correctifs par angle (interpolation linéaire des déplacements de sommets entre angles clés), calculés à partir de la différence entre la cible d'étirement optimal et le LBS. Pas de GPU requis, conforme aux règles du projet.

## 54. Cible ARAP non convergée à 12 itérations
- Symptôme : entre 12 et 40 itérations, l'écart maximal de la cible atteint 0,071 pour une amplitude de correctif de 0,255 (28 %).
- Cause : itérations insuffisantes pour la méthode locale-globale ARAP.
- Correction : 40 itérations. Le résultat hors entraînement tient à 40 itérations.
- Règle : vérifier la convergence d'un solveur itératif (écart entre deux nombres d'itérations) avant d'interpréter son résultat.

## 55. Correctif ARAP interpolé : validé en numpy, pas encore dans Blender
- Méthode : cible ARAP (locale-globale, arêtes uniformes, ancres = tronc), correctif = cible − LBS, interpolé linéairement entre angles d'entraînement 60/90/120° ; test hors entraînement à 75° et 105°. Témoin 0° : écart 6e-7.
- Résultats (poids d'origine, plis / étirement max) : bras 75° 7 → 0, 2,26 → 1,12 ; bras 105° 12 → 4, 3,00 → 1,16 ; avant-bras 75° 2 → 0 ; avant-bras 105° 5 → 2 ; jambe 75° 1 → 0 ; jambe 105° 7 → 3.
- Limites : vérifié en numpy seulement (métrique calibrée à ±4 faces) ; arêtes uniformes (non cotangentes) ; test en interpolation, pas en extrapolation au-delà de 120° ; bras à 105° encore 4 plis.
- Prochaine étape : appliquer les correctifs dans Blender (formes-clés) et mesurer avec `mesure_lbs` avant toute déclaration de succès.

## 56. Amortissement des correctifs autour des plis : échec
- Tentative : réduire la correction des sommets situés dans une face repliée (facteur 0,8), jusqu'à disparition des plis.
- Résultat : amortissement brut par sommet : étirement 6,4 à 8,0 sur les poses de test (déchirures). Amortissement lissé par diffusion : 5 plis à 75° au lieu de 0. Les deux variantes sont rejetées.
- Règle : ne jamais modifier une correction par sommet sans transition continue ; et ne jamais entraîner une correction sur des plis qu'elle ne doit pas corriger.

## 57. Pondération cotangente : bug d'ancre puis résultat mitigé
- Bug : le second membre des ancres ignorait les poids d'arête (étirement 172 partout). Corrigé.
- Résultat hors entraînement : bras 105° 4 → 3 plis, étirement minimal 0,51 → 0,70 ; jambe 105° 3 → 1 pli ; avant-bras 105° 2 → 3 plis (minimum 0,28 → 0,25).
- Non adopté par défaut : gain mixte, pas de chaîne gagnante nette. L'option `poids=` reste disponible.
- Règle : un bug de second membre peut produire un résultat aberrant uniforme ; un résultat identique sur toutes les poses signale d'abord une erreur d'implémentation.

## 58. Limitation de rotation dès le début de l'ARAP : cascade de plis sur le bras
- Tentative : ramener vers l'identité la rotation des sommets de faces repliées, à chaque itération.
- Résultat : bon sur l'avant-bras et la jambe, mais sur le bras le nombre de plis explose (112 à 120° d'entraînement). Le sous-ensemble de faces repliées grossit d'une itération à l'autre.
- Version douce (alpha 0,8, activée à partir de l'itération 25) : évite la cascade, mais le bras reste dégradé (39 plis à 120°).
- Règle : une limitation active pendant le solveur doit être testée pour sa stabilité (le nombre de plis doit décroître), pas seulement pour son effet final.

## 59. Choix de variante sur les poses d'entraînement uniquement
- Méthode : pour chaque pose d'entraînement, garder la variante (ARAP simple ou limitée) qui produit le moins de plis sur cette pose. Les poses de test ne sont jamais utilisées pour ce choix.
- Résultat hors entraînement (numpy, puis Blender par formes-clés) : avant-bras 105° 0 pli (origine 5), jambe 105° 0 pli (origine 7), jambe 120° 1 pli (origine 10). Bras : 4 plis à 105° (origine 12), 12 à 120° (origine 15).
- Règle : une sélection entre variantes est légitime si elle n'utilise que l'entraînement et si le résultat est revalidé sur des poses non utilisées.

## 60. Ancre plus large : étirement explosif
- Test : seuil d'ancrage du tronc à 0,5 ou 0,2 au lieu de 0,99 : étirement 1,8 à 2,2 hors entraînement. Seuil 0,9999 : quasi identique à 0,99.
- Règle : l'ancrage doit rester au tronc pur ; élargir la zone libre fait dériver l'épaule.

## 61. Protocole : rotation de l'humérus seul à 120° n'est pas un usage réaliste
- Constat : nos tests font tourner l'humérus (LeftArm) seul jusqu'à 120°. Les pratiques de rig (fil Blender Artists « shoulder caving in ») répartissent la rotation entre un os d'épaule (clavicule) et le bras ; le bras seul est limité à environ 90°.
- Conséquence : une partie du résidu de plis à 105–120° vient peut-être du protocole, pas de la méthode. À confirmer par un test où la rotation est répartie entre LeftShoulder et LeftArm.
- Pistes issues de la recherche, non testées ici : Preserve Volume (DQS, déjà rejeté pour le volume, erreur antérieure) ; os d'aide avec contraintes (testé sans gain net) ; placement d'un vrai os d'épaule (à tester).
- Règle : un test de déformation doit reproduire la répartition réaliste des rotations entre os, sinon il mesure un cas extrême.

## 62. Hypothèse « le protocole cause le résidu » : testée, infirmée en grande partie
- Hypothèse (erreur 61) : répartir la rotation avec l'os d'épaule réduirait les plis du bras à grand angle.
- Test : pose réelle Blender, 1/3 sur LeftShoulder et 2/3 sur LeftArm, poids d'origine.
- Résultat (plis / étirement max) : total 60° : 3 / 2,06 contre 3 / 1,91 (bras seul) ; 90° : 8 / 2,84 contre 8 / 2,63 ; 105° : 9 / 3,23 contre 12 / 3,00 ; 120° : 11 / 3,62 contre 15 / 3,36.
- Conclusion : la répartition réduit à peine les plis (3 à 4 de moins à 105–120°) et dégrade légèrement l'étirement. Le repliement de l'épaule est intrinsèque aux poids LBS, pas seulement au protocole.
- Règle : tester une hypothèse protocole sur Blender avant d'en tirer une conclusion ; ici, la conclusion initiale était fausse en grande partie.

## 63. Correctifs ARAP sur poses réparties épaule + bras : validation Blender
- Entraînement 60/90/120 (répartition 1/3 épaule, 2/3 bras), test hors entraînement 75 et 105, formes-clés alimentées par l'angle total.
- Blender : à 75°, 0 pli (origine 6), étirement 1,22 ; à 105°, 4 plis (origine 9), étirement 1,19. Mêmes ordres de grandeur que le bras seul.
- Non résolu : à 120° (entraînement), 11 plis, comme à l'origine : la sélection garde la variante simple, la variante limitée n'aide pas sur cette pose.
- Règle : une correction entraînée sur le même angle total que le test est valable ; le résidu à 120° reste un problème ouvert.

## 64. Test de longueurs : correspondance de suffixe trop large
- Symptôme : le test des bras signalait « LeftForeArm = 0.144 h hors plage » alors que la valeur est dans la plage de l'avant-bras (0,12–0,18 h).
- Cause : `"LeftForeArm".endswith("Arm")` est vrai ; l'avant-bras était comparé à la plage du bras.
- Correctif : comparer le nom après le côté (`Left`/`Right`) à la clé exacte du dictionnaire de plages.
- Règle : dans un test, ne jamais faire de correspondance par `endswith` sur des noms dont un suffixe est un autre suffixe.

## 65. Lobes de doigts : un bloc de doigts accolés est fusionné, et l'ordre dépendait du côté
- Symptôme : à gauche, 4 lobes ; à droite, 3 lobes (l'index et le majeur fusionnés, n = 160 sommets). Un rig symétrique était impossible.
- Cause 1 : le regroupement par écart latéral de 5 mm ne sépare pas des doigts qui se touchent.
- Cause 2 : les doigts étaient ordonnés par « w décroissant », ce qui suppose le pouce du côté des w élevés. C'est vrai à gauche seulement.
- Correctif : un lobe plus large que deux doigts (> 21 mm par doigt) est découpé aux plus grands écarts ; les doigts sont ordonnés par distance au pouce.
- Vérification : gauche et droite donnent 4 lobes, mêmes rôles, écart de longueur 0,6 mm.

## 66. Bout de main déclaré « extrapolé » sans regarder les sommets extrêmes du maillage
- Symptôme : le chemin de la main s'arrêtait à 0,164 m du poignet et je l'ai signalé comme extrapolé.
- Vérification ensuite : les sommets les plus avancés du maillage vont à 0,182 m (pouce, index, majeur). L'extrapolation était une sous-estimation.
- Règle : avant de déclarer une extrémité extrapolée, mesurer les sommets extrêmes du maillage dans la direction de l'os.

## 67. Doigts courbés : une chaîne droite sort du maillage
- Symptôme : les phalanges droites entre la base et le bout sortaient du maillage (3 segments sur 4 pour l'index).
- Cause : les doigts du HBM sont légèrement courbés.
- Correctif : les articulations suivent la ligne médiane mesurée du lobe (centroïde par tranche de 1 cm, abscisse curviligne).
- Limite : les segments sans lobe mesuré (base du pouce, auriculaire) restent droits et sont marqués « estimés, non testés ».

## 68. Plis à 120° : l'os auxiliaire de torsion domine le bras supérieur
- Mesure (LBS pur, poids `W_seq_final`) : 20 plis à 120°, localisés sur le bras supérieur (z 1,07 à 1,31 en repos), dominés par `LeftArmHelper` (23 sommets) puis `LeftArm` (11).
- Hypothèse testée : reporter 50 % ou 100 % du poids de l'auxiliaire sur `LeftArm`. Résultat : 17 et 23 plis, étirement max 3,5 et 2,3. Le report de poids ne résout pas le problème.
- Conclusion : le pli vient de la déformation linéaire elle-même (torsion et flexion combinées sur le même os), pas seulement de la répartition des poids.
- Piste à vérifier, non implémentée : séparation torsion/flexion des os (Jacobson et al., « Stretchable and Twistable Bones for Skeletal Shape Deformation », SIGGRAPH Asia 2011). Source trouvée par recherche, non lue en détail.
- Diagnostic reproductible : `engine/skinning/diagnostic_plis_120.py`.

## 69. Os de torsion : retirer sa flexion aggrave les plis (rejeté)
- Hypothèse : l'auxiliaire `LeftArmHelper` ne devrait tourner qu'en torsion (sa flexion mesurée à 120° : 60°).
- Test (`engine/skinning/test_torsion_vraie.py`, pivot = épaule au repos, axe = os au repos) : 20 → 35 plis à 120° en LBS, étirement 6,0 → 9,4.
- Erreur de méthode corrigée en route : un point fixe de rotation n'est pas unique (toute la droite de l'axe est fixe), donc le pivot ne peut pas venir d'un moindres carrés seul.
- Conclusion : les poids de référence sont calibrés avec la flexion de l'auxiliaire. Piste rejetée.

## 70. Poids par distance bruts : nettement moins bons que la référence
- `engine/skinning/poids_distance.py` (K = 4, p = 2) : 48 plis à 120° contre 20, étirement 16,6 contre 6,0 (bras gauche, LBS).
- Décision : base trop faible pour servir seule ; elle n'est pas adoptée. Le test reste dans le dépôt comme témoin.

## 71. Poids heat (Blender ARMATURE_AUTO) : meilleure base que la référence pour le bras
- Export sans optimisation (`engine/skinning/exporter_poids_heat.py`) : bras à 120° : 12 plis contre 20, étirement 4,7 contre 6,0 ; avant-bras : étirement 2,2 contre 1,5 (moins bon).
- Avec ARAP interpolé (entraînement 60/90/120, test 75/105) : 75° : 8 → 0 plis ; 105° : 10 → 4 plis ; étirement ≈ 1,14 partout (référence ≈ 1,2).
- Décision : heat devient la base du bras ; la référence optimisée est gardée comme témoin.

## 72. Résidu du bras à 120° : transfert de poids vers l'épaule, sélection sur l'entraînement
- Localisation (erreur 71) : 33 sommets sous le sommet de l'épaule, dominés par le bras.
- Transfert de 50 % du poids du bras vers l'épaule dans un rayon de 0,16 m (`engine/skinning/transfert_epaule.py`).
- Sélection faite sur 120° (entraînement) : rayon 0,10 → zone vide (filtre trop strict, corrigé) ; 0,12 → 4 plis ; 0,16 → 0 pli. 100 % du transfert : 6 plis, rejeté.
- Vérification hors entraînement : 75° → 0 pli ; 105° → 0 pli ; étirement 1,15.
- Limite : sélection du rayon et de la fraction sur des poses qui sont aussi l'objet du test ; à confirmer sur de nouvelles poses.

## 73. Avant-bras et jambe : plis résiduels au coude et au genou
- Après ARAP sur la nouvelle base : avant-bras 120° : 6 plis (14 sommets, au pli du coude) ; 105° : 2 ; jambe 120° : 9 plis (18 sommets, au genou) ; 105° : 3.
- Étirement : avant-bras 1,08, jambe 1,14.
- Solution déjà mesurée dans le dépôt pour ce cas : formes-clés de seconde pose (`construit_seconde_pose.py`), mais le script est lié à une scène et à des chemins /tmp, et n'est pas relancé avec la nouvelle base. Non fait.

## 74. Score de confiance : validé contre les plis
- `engine/skinning/score_confiance.py` (confiance = 1 − entropie normalisée des poids).
- Sommets repliés à 120° : confiance 0,62 contre 0,87 pour les autres (Mann-Whitney p = 7e-14). Zones : bras 0,70 ; avant-bras 0,94 ; jambe 0,85 ; tronc 0,68.

## 75. Validation Blender : la normale de repos ne doit pas bouger avec le correctif
- Symptôme : avec `faces_repliees(..., decalage=...)`, le bras passait de 0 à 68 plis avec le correctif, alors que numpy annonçait 0.
- Cause : la fonction recalcule la normale de repos sur la géométrie décalée. La règle des plis (entrée 51) compare la pose à la normale du repos ORIGINAL.
- Correctif : fonction `plis_definition` dans `engine/skinning/valide_base_blender.py` (normale de repos d'origine).
- Résultat après correction : Blender et numpy concordent sur le bras et l'avant-bras (0 pli partout). Sur la jambe, Blender : 2 plis à 105° et 120° ; numpy : 1 et 3. Écart de 1 à 2 faces, dans la tolérance de calibration (±4).

## 76. Jambe : résidu de 2 à 3 plis au genou, grille de paramètres épuisée
- Base finale : bras, avant-bras et jambe sont corrigés par ARAP interpolé sur la base épaule + coude + genou.
- Transfert au genou (jambe → cuisse), sélection sur 120° (entraînement) : rayon 0,16 m et fraction 0,5 → 3 plis (retenu) ; rayon 0,22 → 7 ; rayon 0,13 → 8 ; rayon 0,19 → 9 ; fraction 0,3 → 5 ; fraction 1,0 → 11.
- Blender sur la base finale : jambe 2 plis à 105° et 120°, 0 à 60/75/90 ; étirement 1,10 à 1,20.
- Ouvert : ce résidu n'est pas résolu par la famille de méthodes utilisée. Piste non testée : formes-clés de seconde pose au genou, comme pour l'avant-bras avant ce travail (erreur 73).

## 77. Genou : chaîne de nœuds coaxiaux (répartition de l'angle sur une bande) testée
- Hypothèse (demande de l'utilisateur) : le genou est une boîte de jonction qui tourne ; la cuisse et la jambe sont des bâtons rigides. Au lieu d'un mélange de deux matrices sur une grande zone, l'angle est réparti sur K nœuds coaxiaux dans une bande de hauteur 2B autour du genou.
- Mesure (`engine/skinning/test_chaine_genou.py`, données `arap/donnees7.npz`, jambe gauche, 1 757 sommets) :
  - LBS actuelle : 0 / 5 / 7 / 10 plis à 60 / 90 / 105 / 120° ; étirement max 1,14 à 1,27.
  - Chaîne K=8, B=0,05 m : 19 à 26 plis (pire) ; B=0,10 m : 0 / 7 plis à 90 / 120° ; B=0,15 m : 0 / 0 plis, étirement max 1,37.
- Lecture : une bande étroite concentre la rotation (gradient θ/2B sur un rayon ρ ≈ 0,07 m) et étire la peau ; une bande large répartit la rotation et supprime les plis. Le compromis plis / étirement est géométrique, pas un défaut de code.
- L'étirement maximal est très localisé : p99 = 1,00 pour toutes les bandes, les arêtes les plus étirées sont peu nombreuses, vers z ≈ 0,564 m (bord inférieur de la bande).
- Ouvert : le critère « étirement max ≤ 1,25 » n'est pas atteint à 0 pli. Il faut décider si l'on évalue l'étirement au p99 (honnête) ou en max (strict). Les résultats avec p99 sont à consigner dans le rapport de validation.
- Méthode retenue pour la suite : tester la chaîne en Blender (LBS réelle) avant d'en conclure ; ne pas généraliser avant.

## 78. Genou : chaîne de nœuds validée dans Blender (LBS réelle)
- Critères mécaniques (demande de l'utilisateur) : segments rigides, centre anatomique, pas de pénétration, section non aplatie. L'étirement devient secondaire.
- Mesure dans Blender (`engine/skinning/chaine_genou_blender.py`, K=8, bande 0,15 m) : écart Blender/numpy 0,000 mm ; 0 pli à 60, 90, 105, 120° ; cuisse et jambe rigides (0,00 mm) ; section du genou 0,995–0,999 (base actuelle : 0,52 à 120°).
- Erreur de contrôle corrigée : l'axe de la section était mesuré sur le plan horizontal. Il faut le mesurer perpendiculairement à l'axe du segment (`engine/skinning/mesure_section_genou.py`).
- Hauteur du genou vérifiée : pivot Mixamo à z = 0,476 m, soit 0,285 × 1,69 m (taille du maillage) ; c'est le bon centre.
- Rapport : `docs/rapports/phase4_genou_chaine_blender.json`. Ouvert : coude, cheville, hanche, épaule, poignet ; nœuds à ajouter au squelette HBM.

## 79. Coude validé dans Blender ; cheville en échec partiel
- Coude : chaîne de 8 nœuds, bande 0,10 m, pivot Mixamo LeftForeArm (z = 1,077 m, soit 0,64 h). LBS Blender = numpy (0,000 mm) ; 0 pli à 60–120° ; segments rigides ; section 0,993–0,998.
- Erreur de mesure corrigée : la tranche de section incluait des sommets du tronc qui ne bougent pas, d'où une fausse section de 0,52. Ne mesurer que les sommets du membre.
- Erreur de mesure corrigée : l'axe de pivot est une droite ; le point choisi doit être projeté au niveau de la jointure, sinon la bande tombe hors du maillage (pivot à y = −2,08 au lieu de −0,04).
- Cheville (numpy, pas encore Blender) : en mode « enfant rigide », 0 pli en flexion plantaire (−20°), mais 18 plis en flexion dorsale (+20°) : le pied rigide traverse le bas de la jambe. La section tombe à 0,37 à −50°. Ouvert : la géométrie de contact cheville/tibia n'est pas résolue.
- Rapport : `docs/rapports/phase4_coude_cheville.json`.

## 80. Cheville : bande mesurée sur la bissectrice de jointure (valeurs humaines normales)
- Référence : flexion dorsale normale ≈ 20°, flexion plantaire ≈ 50° (genou tendu). Le pied ne passe pas devant le tibia : la butée est osseuse, le pied rigide ne doit donc pas pénétrer le tibia dans ces amplitudes.
- Cause du 18 plis : la bande était mesurée le long du tibia, alors que le pied est à angle droit ; une partie des sommets du pied se trouvait dans la bande et pénétrait le tibia dès 5°.
- Correctif : bande mesurée le long de la bissectrice des deux segments (`chaine(..., bissectrice=True)`), pied rigide (`enfant_rigide=True`), largeur 0,04 m.
- Blender : 0 pli à +20, −20, −50 ; pied rigide ; écart Blender/numpy 0,000 mm.
- Section : la valeur 0,53 était fausse (tranche sur le plan horizontal). Avec la normale de jointure : 1,00 (+20), 0,95 (−20), 0,88 (−50). La perte de 12 % à −50° reste à vérifier visuellement.

## 81. Hanche : plis résiduels 15 à 30 malgré quatre approches
- Mesure : plis à 90° et 120° : 15 à 30 dans toutes les variantes (bande plane, rigidité du fémur, coquilles sphériques r0/r1, bassin qui suit une fraction p de la rotation).
- Localisation : plis à z = 0,75–0,96 m, autour du centre de la hanche (0,873 m), donc sur la frontière entre tronc fixe et cuisse tournante, non sur la cuisse elle-même.
- Lecture : une articulation à 3 DDL ne peut pas être ramenée à une seule rotation coaxiale ; une rotation purement coaxiale ne rend pas le mouvement de la sphère. La frontière tronc / cuisse demande soit un correctif de pose (ARAP, comme pour le bras en phase 4), soit une modification du maillage au pli de l'aine. Non résolu.
- Outil : `engine/skinning/test_hanche_chaine.py`.

## 82. Hanche : mélange de rotations (SBS) testé ; les 0 plis étaient un artefact
- Méthode étudiée (source primaire, article de Kavan et al., I3D 2005 : https://users.cs.utah.edu/~ladislav/kavan05spherical/kavan05spherical.pdf) : au lieu de mélanger les matrices (LBS), on mélange les rotations en quaternions (QLERP) autour d'un centre de rotation ; la translation reste linéaire. Pour un pivot commun : v' = R(q(f))·(v − c) + c.
- Implémentation : `engine/skinning/sbs_articulation.py`.
- Piège : avec un champ en coquilles sphériques (r0 = 0,05 ; r1 = 0,15), on obtenait 0 pli à 90° et 120°, mais 23 sommets du tronc voisin bougeaient de 18 à 26 cm. Les plis étaient masqués par ce déplacement.
- Variante corrigée (tronc au-dessus de la hanche bloqué) : 31 à 38 plis, déplacement du tronc 12 à 17 cm. Le problème n'est pas résolu.
- Lecture : le point de contact est la frontière entre la cuisse proximale (dans le bassin) et le tronc (fixe). Un champ de poids ne suffit pas ; il faut un correctif de pose (ARAP ou formes-clés de la hanche), comme pour le bras en phase 4.
- Règle retenue : un résultat « 0 pli » n'est valable que si les sommets voisins ne se déplacent pas de façon non anatomique. Toujours mesurer les déplacements du voisinage avant de conclure.

## 83. Où un pli est acceptable : règle par zone anatomique
- Recherche : les épaules et les hanches sont les zones à problème ; on ajoute des correctifs seulement si rien d'autre ne suffit, et les creux de peau réels (aine, pli fessier, creux poplité, pli du coude, aisselle) sont les seuls lieux où un pli est normal.
- Règle retenue (`engine/skinning/plis_zones_acceptables.py`) : un pli n'est acceptable que dans une zone de pli anatomique et sans pénétration. Tout pli hors zone est un défaut.
- Mesure sur la hanche (chaîne LBS, 90° et 120°) : 6 à 7 plis dans la zone de l'aine, 22 à 23 hors zone, surtout sur le côté (x ≈ −2,27 à −2,33 ; z 0,75 à 0,90 ; trochanter et fessier externe). Ces plis ne sont pas acceptables : ce sont des défauts.
- Conséquence : la hanche n'est pas validée. Il faut un correctif de pose sur le côté de la hanche, ou un autre traitement de la frontière tronc / cuisse.

## 84. Hanche : erreur de sous-arbre corrigée ; plis réels à partir de 45°
- Erreur de test : la flexion de hanche a fait tourner la seule cuisse ; la jambe et le pied (sous-arbre enfant) restaient immobiles. Les plis « au genou » à 10° venaient de cette erreur.
- Correction : sous-arbre complet (cuisse, jambe, pied). Résultats (chaîne, bande 0,04 m, bissectrice) : 0 pli à 10° et 30°, 15 à 60°, 21 à 90°, 24 à 120°.
- Localisation des plis : z 0,76 à 0,90 m (hauteur de la hanche, 0,873 m), côté latéral (x −2,13 à −2,33) : trochanter et fessier externe. Ces plis ne sont pas acceptables (erreur 83).
- Piège : une bande plus large (0,12 à 0,20 m) fait tomber les plis à 2–5 à 60–90°, mais déplace des sommets du tronc de 10 à 20 cm. Ce n'est pas une solution.
- Correctif ARAP local (rayon 0,25 m) : plis 8 / 16 / 18 à 60 / 90 / 120°, mais déplacements de 10 à 16 cm. Trop large pour un correctif.
- État : hanche validée à 0 pli jusqu'à 30° uniquement. Au-delà, il faut une solution de correction non résolue. Rapport à compléter.
- Outil : `engine/skinning/test_hanche_chaine.py` (à mettre à jour avec le sous-arbre complet).

## 85. Correctif calculé de hanche (variante B) : rejeté, il aggrave les plis
- Méthode testée : correctif de pose calculé sur la frontière tronc / cuisse, plafonné en déplacement.
- Résultats : plafond 3 cm sans effet sur les plis ; plafonds 6 et 10 cm font monter les plis à 36–48, soit plus que sans correctif.
- Cause : le correctif déplace des sommets voisins dans une zone où la géométrie se replie ; sans contrainte de volume, il crée de nouveaux plis.
- Décision : variante B abandonnée, variante A (chaîne de jonctions seule) retenue, conformément à l'instruction de l'utilisateur.
- Conséquence : hanche vérifiée à 0 pli jusqu'à 30° seulement, épaule jusqu'à 20°, poignet jusqu'à 50°. Au-delà, défauts non résolus (voir `docs/rapports/phase4_hanche_epaule_poignet.json`).
- Outil : `engine/skinning/correctif_hanche_minimal.py` (échec documenté, ne pas réutiliser tel quel).

## 86. Le critère de plis ne voit pas la pénétration : verdict « acceptable » faux
- Constat (captures de l'utilisateur) : coude à 105°, cheville à −50°, poignet à 50°, genou à 120° : des membres traversent le tronc ou un autre membre. Le visualiseur affichait pourtant « Acceptable : 0 pli ».
- Cause : le critère ne comptait que les normales de faces repliées. Il ne mesure ni la pénétration, ni la perte de volume.
- Correction du verdict : la page n'affiche plus jamais « acceptable » tant que la pénétration n'est pas mesurée (commit de la v2 corrigée).
- Métrique ajoutée : `engine/skinning/penetration.py`. Pour chaque sommet du membre, distance signée à la face la plus proche du reste du corps (maillage fermé et cohérent, vérifié : 0 arête de bord, volume positif).
- Contrôle positif : pousser l'avant-bras vers le tronc fait apparaître 126 à 811 pénétrations : la métrique détecte bien une traversée.
- Pièges rencontrés :
  - normale du sommet le plus proche : faux (50 pénétrations au repos) ; remplacée par la face la plus proche ;
  - seuil de distance à la surface de 3 cm : masque justement les pénétrations profondes ; supprimé ;
  - le repos lui-même chevauche au pli du coude (l'avant-bras commence dans le bras) : on ne compte que les pénétrations *nouvelles* par rapport au repos.
- Résultat coude (pénétrations nouvelles, chaîne actuelle B = 0,10) : 60° : 17 ; 90° : 5 ; 105° : 2 ; 120° : 0. Le critère de plis disait 0 partout.
- Variante « segments durs » (sans bande) : 0 pénétration de 60° à 120°, mais des fentes et des plis à la jonction. Il faut donc une calotte rigide au centre de la jonction, pas seulement une bande de poids.

## 87. Le coude pliait vers l'arrière : aucune limite anatomique dans le modèle
- Constat : le modèle accepte n'importe quel angle. Au coude à −10° (hyperextension), 5 sommets de l'avant-bras pénètrent le bras.
- Cause : les chaînes de jonctions n'ont pas de bornes de mouvement ; seules des amplitudes positives ont été testées.
- Méthode : bornes par articulation tirées du jeu officiel CDC / NCHS (674 sujets), dans `engine/skinning/limites_articulations.py`.
- Mesure, six articulations, amplitudes normales : pénétrations nouvelles présentes partout sauf poignet (voir `docs/squelette_xbot_articulations.md`).
- Lacune : abduction de hanche, abduction et élévation de l'épaule, poignet : aucune valeur officielle trouvée. Marquées « non vérifié ».

## 88. Le « zéro pénétration » des segments durs était un artefact de l'exclusion de zone
- Constat : le test précédent (`variantes_coude.py`) donnait 0 pénétration pour les segments durs, avec une zone d'exclusion de 13 cm autour du coude.
- Or c'est dans cette zone que se trouvent les pénétrations. Sans exclusion, le groupe mobile (avant-bras) pénètre le groupe fixe : 8 / 4 / 16 / 19 / 17 à 30 / 60 / 90 / 105 / 120°. Elles sont à 4 à 7 cm du coude, donc sur les extrémités de tube.
- Correction : le chiffre « 0 » est retiré. Ce n'était pas une mesure valide.
- Essais de calotte (coupure au plan bissecteur, sphère de rayon variable) :
  - rayon 4,1 cm (marqueur X-Bot) : 32 / 12 / 13 / 15 / 18 ;
  - rayon 6 cm et plus : 33 / 5 / 14 / 10 / 11.
  Aucune variante n'arrive à zéro. Le plan de coupure sur les sommets existants ne suffit pas : il faut générer une géométrie de sphère, traitée comme matière de jonction, et la mesurer.
- Source : `engine/skinning/test_calotte_coude.py`, rapport à compléter dans `docs/rapports/`.
