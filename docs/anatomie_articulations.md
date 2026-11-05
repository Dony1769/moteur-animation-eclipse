# Anatomie des articulations : référence pour le squelette du moteur

Source : connaissances anatomiques courantes (manuels d'anatomie fonctionnelle, Kapandji, classification des
articulations). Les amplitudes sont des ordres de grandeur adultes, arrondis ; elles doivent être confirmées
par une source officielle avant d'être figées dans le rig (voir section « Vérification »).

## 1. Principes communs
- Une articulation = deux segments osseux + une surface de contact + des ligaments qui limitent le mouvement.
- Degrés de liberté (DDL) : charnière = 1 axe ; condylienne = 2 axes ; sphérique (rotule) = 3 axes ; selle = 2 axes avec couplage.
- Chaque articulation a une amplitude limitée. Aucun segment n'est pliable en son milieu : la flexion se fait
  toujours à la jonction.
- Le rig doit donc séparer : os rigides + nœud de jonction qui porte la rotation.

## 2. Membre inférieur
| Articulation | Reliant | Type | DDL | Amplitude (adulte, ordre de grandeur) |
|---|---|---|---|---|
| Sacro-iliaque | bassin / sacrum | quasi-fixe | ~0 (mouvement très faible) | 2–3° |
| Hanche (coxo-fémorale) | bassin / cuisse | sphérique | 3 | flexion ~120°, extension ~20–30°, abduction ~40–45°, adduction ~20–30°, rotation interne/externe ~30–45° |
| Genou (fémoro-tibiale + fémoro-patellaire) | cuisse / jambe | charnière (+ rotation secondaire) | 1 (+ rotation ~10–15° en flexion) | flexion ~130–140°, extension ~0° (pas d'hyperextension normale) |
| Cheville (tibio-talienne) | jambe / talus | charnière | 1 | flexion dorsale ~20°, flexion plantaire ~45–50° |
| Sous-talienne | talus / calcanéus | rotation complexe | 2 couplés | inversion ~20–30°, éversion ~10–20° |
| Médio-tarsienne et tarsométatarsienne | pied | glissement | ~1 par ligne | petites amplitudes, répartition du pied |
| Métatarso-phalangiennes (MTP) | pied / orteils | condylienne | 2 | flexion ~35–45°, extension ~70° (gros orteil plus) |
| Interphalangiennes (IP) | orteils | charnière | 1 | flexion ~40–60° (gros orteil : 1 seule IP) |

## 3. Membre supérieur
| Articulation | Reliant | Type | DDL | Amplitude (ordre de grandeur) |
|---|---|---|---|---|
| Sterno-claviculaire | sternum / clavicule | sellaire | 3 | mouvement de la clavicule, ~30° |
| Acromio-claviculaire | clavicule / omoplate | plane | 3 | ~20–30° |
| Scapulo-thoracique | omoplate / cage thoracique | glissement (pas une vraie articulation) | 3 | élévation, rotation haut |
| Gléno-humérale (épaule) | omoplate / humérus | sphérique | 3 | flexion ~180°, extension ~50–60°, abduction ~180° (avec omoplate), rotation ~90° chaque sens |
| Huméro-ulnaire (coude) | humérus / ulna | charnière | 1 | flexion ~140–150°, extension ~0° |
| Radio-ulnaire proximale et distale | radius / ulna | pivot | 1 | pronation ~80–90°, supination ~80–90° |
| Radio-carpienne (poignet) | radius / carpe | condylienne | 2 | flexion ~80°, extension ~70°, inclinaison radiale ~20°, ulnaire ~30–40° |
| Carpo-métacarpiennes et intercarpiennes | carpe / métacarpes | glissement | ~1 par ligne | petites amplitudes, cambrure de la main |
| Métacarpo-phalangiennes (MCP) | métacarpe / phalange | condylienne | 2 | flexion ~90°, extension ~30–45° |
| Interphalangiennes proximales (PIP) | phalange 1 / 2 | charnière | 1 | flexion ~100–110° |
| Interphalangiennes distales (DIP) | phalange 2 / 3 | charnière | 1 | flexion ~70–80° |
| Pouce (CMC, sellaire ; MCP ; IP) | trapèze / métacarpe 1 | sellaire + charnière | 2 à 3 | opposition complexe |

## 4. Tronc et cou
| Articulation | Type | DDL | Amplitude (ordre de grandeur) |
|---|---|---|---|
| Lombaires (L1–L5) | segments en série | 3 par étage | flexion ~60°, extension ~25°, rotation ~5° par étage |
| Thoraciques (T1–T12) | segments en série | 3 par étage | rotation la plus importante ici ; flexion faible |
| Cervicales (C1–C7) | segments en série ; C1-C2 spécial (rotation) | 3 par étage | flexion ~45°, rotation ~70–80° au total |
| Atlanto-occipitale (tête / C1) | condylienne | 2 | flexion-extension ~25° + ~10° |

## 5. Conséquences pour le rig du moteur
1. Les **six articulations importantes** du membre inférieur et supérieur (hanche, genou, cheville, épaule,
   coude, poignet) reçoivent un nœud de jonction chacune.
2. Les **articulations secondaires** (orteils, doigts, pouce, colonne) sont des chaînes de nœuds ; leurs
   amplitudes sont bornées pour éviter le pliage dans le corps.
3. Les **pivots** (radio-ulnaire) donnent une rotation axiale de l'avant-bras, séparée de la flexion du coude :
   c'est une source de déformation fréquente si elle est confondue avec la flexion.
4. Les **mouvements couplés** (sous-talienne, scapula, lombaires) sont traités comme une rotation combinée
   d'un seul nœud, pas comme plusieurs axes indépendants.
5. Le **tronc** est une chaîne de segments courts plutôt qu'un bâton : sans nœuds intermédiaires, la
   courbure de la colonne ne peut pas exister.

## 6. Liste de nœuds à créer dans le squelette HBM
- Membre inférieur (×2) : HipJoint, KneeJoint, AnkleJoint, SubtalarJoint, ToeMTP (5 par pied) et ToeIP.
- Membre supérieur (×2) : ClavicleJoint, ShoulderJoint, ElbowJoint, ForearmPivot, WristJoint, MCP/PIP/DIP (fingers, déjà en place).
- Tronc : Lumbar (L1–L5 en chaîne), Thoracic (T1–T12 en chaîne), Cervical (C1–C7), Atlas (tête).

## 7. Vérification (à faire avant de figer)
- Confirmer les amplitudes avec une source officielle (publication scientifique ou manuel d'anatomie
  reconnu) et consigner la source ici, avec la date.
- Confirmer le nombre de vertèbres et de segments avec l'anatomie de référence (24 vertèbres mobiles + sacrum).
