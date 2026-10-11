# QuizMed : architecture (livrable 2/6)

> **Statut** : proposition à valider.
> **Ce qui existe et a été exécuté** : schéma JSON, pipeline Python (`extract`, `validate`, `stamp`), cours de démo fictif, 40 tests qui passent.
> **Ce qui n'existe pas encore** : l'app iOS (livrable 3). Aucun code Swift n'a été compilé : je travaille sur Windows, la compilation se fera sur ton Mac.

## 1. Décisions déjà prises avec toi

| Sujet | Décision |
|---|---|
| Cours | Les 34 dossiers UE du Drive sont vides. On développe sur un **cours de démo fictif et non médical** (`kind: "demo"`, bandeau « Contenu de démonstration » dans l'app). Les vrais cours se branchent ensuite sans changer le code. |
| `N-1` | Ancienne version des cours : **ignoré par défaut** (le contenu peut être périmé). |
| Build iOS | Tu as un Mac avec Xcode. Je livre un projet **XcodeGen** (`project.yml`) et un **package Swift local** testable par `swift test`. Tu compiles et tu me colles les erreurs. |
| Génération du contenu | **Claude Code à chaque ajout de cours**, sans clé API. Le script fait tout le déterministe (extraction, abeilles, vérification) ; je rédige questions, fiches, explications et mnémotechniques ici, puis le script les valide. |

## 2. Vue d'ensemble

```
 Drive (miroir local)         PIPELINE (Python, relançable)                  APP iOS 17+
┌───────────────────┐   ┌─────────────────────────────────────────┐   ┌──────────────────────────┐
│ 2026-2027/S1/UE n │   │ scan → extract → bees → structure       │   │ Content/ (JSON + WebP)   │
│  cours.pdf        ├──►│        │                                │   │  lu en lecture seule     │
│ (N-1 ignoré)      │   │        ▼                                │   │            │             │
└───────────────────┘   │ packets ──► Claude Code rédige ──► stamp│   │  QuizCore (Swift pur)    │
                        │            (questions, fiches,   │      │   │  SRS · scoring · quiz    │
                        │             mnémos, explique-moi)▼      │   │            │             │
                        │                          validate ──► build ─►  SwiftData (progrès)   │
                        └─────────────────────────────────────────┘   │            │             │
                                                                      │  App SwiftUI (MVVM)      │
                                                                      │  Widget WidgetKit ◄─ App Group
                                                                      └──────────────────────────┘
```

Deux frontières nettes :

- **Contenu** (JSON, produit par le pipeline) : immuable côté app, identifié par des ids stables.
- **Données utilisateur** (SwiftData) : progression, favoris, notes, jamais mélangées au contenu. Une mise à jour du contenu ne casse donc pas la progression.

## 3. Pipeline de contenu

### 3.1 Étapes

| Commande | Entrée → sortie | État |
|---|---|---|
| `scan` | dossier miroir du Drive → inventaire des fichiers (sha256, pages), `N-1` exclu ; détecte nouveau / modifié | livrable 1 |
| `extract` | PDF → texte par page, blocs positionnés, images, tableaux (`work/pages/<src>.pages.json`), pages PNG | **fait** |
| `bees` | pages rasterisées → positions des abeilles, rattachement à la notion, liste des cas ambigus | livrable 1 |
| `structure` | dossiers + signets + titres → arborescence **proposée** (tu valides) | livrable 1 |
| `packets` | chapitres nouveaux ou périmés → paquets de travail (textes, abeilles, quotas, questions existantes) | livrable 4 |
| *(Claude Code)* | paquet → `questions.json`, `sheet.json`, `mnemonics.json` par chapitre | livrable 4 |
| `stamp` | pose `gen.sourceHash` (empreinte du cours) sur chaque pack généré | **fait** |
| `validate` | schéma + traçabilité + règles métier (voir §3.2) | **fait** |
| `build` | ids, hash anti-doublons, `widgetFriendly`, vérification des mnémotechniques, captures WebP, manifeste, index | livrable 3 |

### 3.2 Garanties contre l'invention

Chaque garantie est une règle vérifiée par `validate`, pas une promesse de prompt (codes d'erreur dans `docs/02-schema-donnees.md`) :

1. **Extrait « Dans le cours »** : copié tel quel, retrouvé mot pour mot sur la page citée. On tolère seulement espaces, apostrophes, tirets, ligatures et césures. Casse, accents et chiffres doivent être identiques, et un mot tronqué est refusé (`jour` n'est pas `jours`). Les `[...]` permettent de sauter un passage, dans l'ordre.
2. **Chaque proposition**, même fausse, a une explication **et** au moins une citation.
3. **Schémas, tableaux, formules** : une capture (zone de la page) et un texte alternatif pour VoiceOver. Pour un tableau, la zone doit recouvrir le tableau détecté (sinon avertissement).
4. **Abeilles** : un badge n'existe que si une abeille est rattachée à la notion. Toute question d'une notion abeille porte le badge, et la fiche doit la mettre en avant.
5. **Mnémotechnique** : la liste enregistrée doit figurer dans l'extrait du cours, dans l'ordre. Le mnémotechnique reprend tous les éléments, dans l'ordre, avec les bonnes initiales, et le texte final est l'assemblage exact des mots (rien ajouté, rien omis).
6. **Doute** : si je ne suis pas sûr à 100 %, la question est générée avec `needsReview` et une raison (badge « À vérifier »). Le validateur refuse un `needsReview` sans raison.
7. **Cours modifié** : `gen.sourceHash` est comparé à l'empreinte actuelle du cours (`W-STALE`). Les questions dont l'extrait n'existe plus sont les seules à réécrire.

### 3.3 Détection des abeilles (livrable 1, à calibrer sur ta vraie page)

1. **Image intégrée** : si l'abeille est une image du PDF, on la retrouve par son empreinte, position exacte (méthode la plus sûre).
2. **Reconnaissance de forme (OpenCV)** : sinon, sur les pages rasterisées, comparaison multi-échelles avec un ou plusieurs modèles du logo. J'ai besoin d'**une page témoin** avec le logo.
3. **Rattachement** : dans une marge, on retient les blocs de texte dont la hauteur recoupe celle de l'abeille. Une abeille dans une ligne se rattache à la phrase. À côté d'un titre, elle se rattache à la section.
4. **Ambiguïté (jamais devinée)** : plusieurs blocs candidats d'égal poids, aucun bloc assez proche, ou score de détection bas. L'abeille part dans la liste « à valider » avec un aperçu et ses candidats. Ta réponse est mémorisée (`validated`) et n'est plus redemandée.

Dans la démo, une abeille est volontairement placée entre deux paragraphes pour tester ce cas.

### 3.4 Incrémental

- L'identité d'un fichier est son **sha256** : nouveau → tout traiter ; inchangé → rien ; modifié → chapitres marqués périmés.
- Les **ids ne sont jamais recalculés** : ils sont attribués une fois et enregistrés. Renommer un chapitre ne perd pas la progression.
- Ajouter un cours n'ajoute que du contenu : les packs des autres chapitres ne sont pas touchés.

### 3.5 Accès au Drive : point à décider quand les cours arriveront

Le connecteur Drive disponible dans Claude Code renvoie les fichiers en base64 **à travers la conversation** : inutilisable pour des PDF de plusieurs Mo (un PDF de 3 Mo ≈ plus d'un million de tokens). Il reste utile pour lister et pour lire du texte. Pour rasteriser les pages et repérer les abeilles, il faut les fichiers **en local**. Trois options :

| Option | Effort | Remarque |
|---|---|---|
| **Google Drive pour ordinateur** en mode miroir | installation unique | Recommandé : les dossiers apparaissent en local, les nouveaux cours aussi. |
| Export ZIP du dossier depuis drive.google.com | à chaque ajout | Aucune installation. |
| API Drive (OAuth) | élevé | Inutile ici : la génération passe de toute façon par Claude Code. |

Formats : le PDF est le format de référence. Un PPTX ou DOCX est converti en PDF (LibreOffice ou export PowerPoint). Un PDF **scanné sans texte** (`textLayer: false`) exige un OCR avant toute génération : le pipeline le signale.

## 4. App iOS

### 4.1 Cibles

```
ios/
├─ project.yml                      XcodeGen → QuizMed.xcodeproj
├─ Packages/QuizCore/               Swift pur, testé par `swift test` (macOS 14+)
│    Content/    modèles Codable du JSON, ContentStore (chargement, index)
│    SRS/        planificateur SM-2, calcul de maîtrise par notion
│    Quiz/       SessionBuilder (entraînement, examen, veille d'exam), Scoring (barèmes)
│    Daily/      DailyQuestionPicker, instantané partagé avec le widget
│    Mnemonics/  vérificateur (même règle que le validateur Python)
├─ QuizMed/                         app SwiftUI (MVVM, @Observable)
│    App/ Features/ DesignSystem/ Data/ (modèles SwiftData, dépôts)  Resources/Content/
├─ QuizMedWidget/                   extension WidgetKit + AppIntents
└─ QuizMedTests/
```

- iOS 17+ : SwiftData, `@Observable`, widgets interactifs, `MagnifyGesture`.
- **Aucun accès réseau** : pas de `URLSession`, pas d'analytics. Hors-ligne par construction.
- La logique métier est dans `QuizCore` (testable sans simulateur). L'app ne contient que vues, ViewModels et persistance.

### 4.2 Couches (MVVM)

| Couche | Rôle | Dépend de |
|---|---|---|
| Views (SwiftUI) | affichage, aucune règle métier | ViewModels |
| ViewModels (`@Observable`) | état d'écran, actions utilisateur | services (protocoles) |
| Services (`QuizCore`) | SRS, sessions, scoring, question du jour | modèles de contenu |
| Dépôts (`Data/`) | lecture/écriture SwiftData, import de l'outbox du widget | SwiftData |
| `ContentStore` | contenu JSON en lecture seule, index, images | bundle |

### 4.3 Navigation

`TabView` à 4 onglets : **Accueil**, **Étudier**, **Révisions**, **Progrès**. Favoris, notes, signalements et réglages sont dans « Plus ».

Un quiz en 2 taps maximum :

- **1 tap** depuis Accueil : « Reprendre » (dernier périmètre), « Réviser (N dues) » ou « Veille d'exam ».
- **2 taps** depuis Étudier : un chapitre, un module ou une UE, puis « Lancer ». La fiche « relire avant » est un bouton secondaire.

Actions principales en bas d'écran (une main), cibles ≥ 44 pt.

### 4.4 Accessibilité et thème

- Dynamic Type par styles de police système, `@ScaledMetric` pour les marges.
- VoiceOver : chaque proposition est lue « A. texte, sélectionnée ». Le badge abeille a le libellé « Notion fréquente au partiel ». Chaque capture lit son `alt`.
- Mode sombre par couleurs sémantiques (assets) : l'ambre de l'abeille a une variante claire et une sombre.
- Les captures s'affichent en zoom pincé et ne sont jamais le seul porteur de l'information (l'`excerpt` ou l'`alt` existe).

### 4.5 Widget et notification

```
 App ──écrit──► App Group/daily.json   (14 jours de questions du jour pré-calculées + corrigé)
 Widget lit daily.json ──► affiche la question
 Tap sur une proposition ──► AppIntent (dans le widget) ──► écrit App Group/outbox/<uuid>.json
 App (au lancement / premier plan) ──► importe l'outbox ──► SwiftData (tentative, SRS, streak)
```

- Le widget **n'ouvre jamais** la base SwiftData (pas de risque de corruption ni de migration croisée).
- Questions à réponse unique (QCU, vrai/faux) : répondre d'un tap. QCM multiples : widget moyen avec bascules puis « Valider » (à valider sur appareil). Repli : lien profond vers l'app.
- **Notification** : 14 notifications locales non répétitives, chacune avec l'aperçu de la question du jour, replanifiées à chaque ouverture et à chaque changement d'heure. Un tap ouvre directement la question (lien profond). iOS limite à 64 notifications en attente : on reste très en dessous.
- Choix de la question du jour : points faibles et notions dues en priorité, bonus abeille, malus si déjà vue récemment ; tirage déterministe par date, donc identique pour le widget, la notification et l'app.

## 5. Couverture de ton cahier des charges

| Demande | Composant | Livrable |
|---|---|---|
| Arborescence + abeilles par chapitre + logos ambigus | `scan`, `extract`, `bees`, `structure` | 1 (outillage prêt dès qu'il y a des cours) |
| Schéma de données et architecture | ce document + `02-schema-donnees.md` + `schemas/` | **2** |
| QCM multiples, QCU, vrai/faux, cas cliniques ; 3 niveaux | schéma `Question` (`type`, `answerMode`, `difficulty`) | 2 puis 4 |
| Explication de chaque proposition + « Dans le cours » + « À vérifier » | `Proposition`, `SourceRef`, `Verify` | 2 (schéma + validateur), 3 (écran) |
| Badge abeille, chapitre incontournable | `Bee`, `priority`, `tier` | 2, 3 |
| Entraînement, favoris, notes, signaler une erreur | SwiftData + écrans | 3 |
| Révision espacée, progression, streak | `QuizCore/SRS`, `NotionStat`, `StreakDay` | 3 |
| Examen blanc chronométré | `SessionBuilder`, `Scoring` (barème à confirmer) | 3 (version simple), 6 |
| Fiches de synthèse | `SheetPack` | 4 |
| Explique-moi | `Question.explain` (analogie étiquetée « hors cours ») | 4 |
| Mnémotechniques (+ le mien à la place) | `MnemonicsPack`, `CustomMnemonic` | 4 |
| Veille d'exam | `SessionBuilder.eve` | 5 |
| Question du jour (widget + notification) | `QuizMedWidget`, `DailyQuestionPicker` | 5 |
| Pipeline relançable | `quizpipe` | 1, 3, 4 |
| 100 % hors-ligne | aucun réseau, contenu embarqué | tous |

## 6. Risques et points ouverts

| Risque | Parade |
|---|---|
| Détection des abeilles imprécise sur le vrai logo | calibrage sur ta page témoin, seuil prudent, rien n'est deviné : le doute va dans la liste à valider |
| PDF scannés (sans texte) | détectés (`textLayer: false`) ; OCR à ajouter avant génération |
| Poids de l'app (images de pages) | on n'embarque que les pages **citées**, en WebP recadré ; le volume réel sera chiffré dès que les cours existent |
| Widget QCM multiple | à tester sur appareil ; repli lien profond |
| Barème des QCM multiples propre à ta fac | à te demander avant l'examen blanc ; configurable (`Scoring`) |
| Droit d'auteur du contenu des cours | usage personnel supposé ; pour partager l'app, accord de la fac nécessaire, et le pack de contenu reste séparable du code |
| Compte Apple développeur gratuit : signature valable 7 jours, capacités limitées | à confirmer avant le livrable 5 (App Group du widget) |

## 7. Questions que je te poserai plus tard (pas bloquantes)

1. Barème exact des QCM multiples de ta fac (avant l'examen blanc).
2. Compte Apple développeur gratuit ou payant (avant le widget).
3. Nom de l'app et identifiant de bundle (avant le projet Xcode : je mets `QuizMed` / `com.example.quizmed` en attendant).
4. Méthode d'accès aux cours (Drive pour ordinateur, ZIP) quand ils seront disponibles.
