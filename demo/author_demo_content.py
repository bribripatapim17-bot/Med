"""Écrit le contenu de DÉMONSTRATION (fictif, non médical) du chapitre « Les planètes ».

Représente ce que produira la génération réelle : questions, fiche, mnémotechnique, chacun cité dans le cours.
Les extraits ci-dessous doivent exister tels quels dans le PDF de démo : c'est `quizpipe validate` qui le vérifie.

    python demo/author_demo_content.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
CH = "ch_demo_planetes"
SRC = "src_demo_planetes"

# Notions : (id, titre, abeille ?, pages citées)
BEE = {"n_demo_ordre_planetes": ["bee_demo_planetes_p1_01"], "n_demo_records": ["bee_demo_planetes_p2_01"]}

# Géométrie relevée par make_demo_course.py
TABLE_BBOX = [0.1176, 0.3444, 0.7647, 0.114]
KEPLER_BBOX = [0.3025, 0.2922, 0.395, 0.0689]

GEN = {"model": "démo rédigée à la main (non générée par un modèle)", "date": "2026-10-11T12:00:00Z", "promptVersion": "demo-0"}

# --------------------------------------------------------------------------- citations réutilisées

ORDRE = ("Le Système solaire compte huit planètes. Dans l'ordre à partir du Soleil : Mercure, Vénus, la Terre, Mars, "
         "Jupiter, Saturne, Uranus et Neptune.")
TELL = "Les planètes telluriques (Mercure, Vénus, la Terre et Mars) sont rocheuses et possèdent une surface solide."
TABLE = ("Telluriques Mercure, Vénus, Terre, Mars Roches et métaux Géantes gazeuses Jupiter, Saturne Hydrogène et hélium "
         "Géantes de glaces Uranus, Neptune Glaces (eau, ammoniac, méthane)")
GEANTES = ("Jupiter et Saturne sont des géantes gazeuses, composées principalement d'hydrogène et d'hélium. "
           "Uranus et Neptune sont des géantes de glaces.")
RECORDS = "Jupiter est la plus grande planète du Système solaire. Mercure est la plus petite."
VENUS = "Vénus est la planète la plus chaude du Système solaire, avec une température de surface d'environ 465 °C."
ANNEE = "La Terre met environ 365,25 jours pour effectuer un tour autour du Soleil."
URANUS = ("L'axe de rotation d'Uranus est incliné d'environ 98° : la planète tourne pour ainsi dire couchée sur le côté.")
KEPLER_TXT = ("Pour une planète en orbite autour du Soleil, le carré de la période orbitale est proportionnel au cube "
              "du demi-grand axe de l'orbite :")
KEPLER_F = "T² = a³ (T en années, a en unités astronomiques)"


def text(label, page, section, excerpt):
    return {"id": label, "sourceId": SRC, "page": page, "section": section, "kind": "text", "excerpt": excerpt}


def table(label):
    return {"id": label, "sourceId": SRC, "page": 1, "section": "2. Classification des planètes", "kind": "table",
            "excerpt": TABLE, "image": {"bbox": TABLE_BBOX},
            "alt": "Tableau : catégories de planètes, planètes concernées et composition principale"}


def formula(label):
    return {"id": label, "sourceId": SRC, "page": 3, "section": "6. Troisième loi de Kepler", "kind": "formula",
            "excerpt": KEPLER_F, "image": {"bbox": KEPLER_BBOX},
            "alt": "Formule encadrée : T au carré égale a au cube, T en années, a en unités astronomiques"}


S_ORDRE = lambda label="s1": text(label, 1, "1. Vue d'ensemble", ORDRE)
S_TELL = lambda label: text(label, 1, "2. Classification des planètes", TELL)
S_GEANTES = lambda label: text(label, 2, "3. Les planètes géantes", GEANTES)
S_RECORDS = lambda label: text(label, 2, "4. Quelques records", RECORDS)
S_VENUS = lambda label: text(label, 2, "4. Quelques records", VENUS)
S_ANNEE = lambda label: text(label, 3, "5. Mouvements des planètes", ANNEE)
S_URANUS = lambda label: text(label, 3, "5. Mouvements des planètes", URANUS)
S_KEPLER_TXT = lambda label: text(label, 3, "6. Troisième loi de Kepler", KEPLER_TXT)


def P(pid, txt, correct, expl, refs):
    return {"id": pid, "text": txt, "correct": correct, "explanation": expl, "sourceRefs": refs}


def Q(notion, typ, diff, stem, props, sources, explain=None, review=None, vignette=None):
    q = {
        "chapterId": CH, "notionId": notion, "type": typ,
        "answerMode": "multiple" if typ == "qcm" else "single",
        "difficulty": diff, "priority": notion in BEE,
    }
    if notion in BEE:
        q["beeIds"] = BEE[notion]
    q["stem"] = stem
    if vignette:
        q["vignette"] = vignette
    q["propositions"] = props
    q["sources"] = sources
    q["verify"] = {"needsReview": True, "reason": review} if review else {"needsReview": False}
    if explain:
        q["explain"] = explain
    return q


def questions():
    qs = []
    # ---- A. ordre des planètes (abeille) -----------------------------------------------------------
    qs.append(Q("n_demo_ordre_planetes", "qcu", 1, "Quelle planète est la plus proche du Soleil ?", [
        P("A", "Mercure", True, "Mercure est citée en premier dans l'ordre à partir du Soleil : c'est la plus proche.", ["s1"]),
        P("B", "Vénus", False, "Vénus vient en deuxième position, juste après Mercure.", ["s1"]),
        P("C", "La Terre", False, "La Terre est la troisième planète à partir du Soleil.", ["s1"]),
        P("D", "Mars", False, "Mars est la quatrième planète, après la Terre.", ["s1"]),
    ], [S_ORDRE()], explain={
        "text": "Le cours donne l'ordre des planètes en partant du Soleil. La première citée, Mercure, est donc la plus proche.",
        "analogy": {"text": "C'est comme la première personne d'une file d'attente : elle est la plus près du guichet.", "label": "hors cours"},
        "sourceRefs": ["s1"]}))
    qs.append(Q("n_demo_ordre_planetes", "qcm", 2,
                "Parmi les propositions suivantes sur l'ordre des planètes à partir du Soleil, lesquelles sont exactes ?", [
        P("A", "Vénus se situe entre Mercure et la Terre.", True, "Dans l'ordre du cours, Vénus est citée après Mercure et avant la Terre.", ["s1"]),
        P("B", "Mars se situe entre la Terre et Jupiter.", True, "Le cours cite Mars après la Terre et avant Jupiter.", ["s1"]),
        P("C", "Saturne est plus proche du Soleil que Jupiter.", False, "Jupiter est citée avant Saturne : c'est Jupiter qui est la plus proche des deux.", ["s1"]),
        P("D", "Uranus est plus éloignée du Soleil que Neptune.", False, "Neptune est citée en dernier, après Uranus : elle est donc plus éloignée.", ["s1"]),
        P("E", "Neptune est la dernière planète de la liste.", True, "Le cours cite Neptune en dernier.", ["s1"]),
    ], [S_ORDRE()]))
    qs.append(Q("n_demo_ordre_planetes", "tf", 1, "Vrai ou faux : la Terre est la troisième planète à partir du Soleil.", [
        P("V", "Vrai", True, "Le cours cite Mercure, Vénus, puis la Terre : elle est bien en troisième position.", ["s1"]),
        P("F", "Faux", False, "L'affirmation est exacte : dans l'ordre du cours, la Terre vient après Mercure et Vénus.", ["s1"]),
    ], [S_ORDRE()]))
    qs.append(Q("n_demo_ordre_planetes", "qcm", 3,
                "Parmi les affirmations suivantes sur le rang des planètes à partir du Soleil, lesquelles sont exactes ?", [
        P("A", "Quatre planètes sont plus proches du Soleil que Jupiter.", True, "Mercure, Vénus, la Terre et Mars précèdent Jupiter dans la liste du cours.", ["s1"]),
        P("B", "Saturne est la sixième planète.", True, "Mercure, Vénus, la Terre, Mars, Jupiter puis Saturne : sixième position.", ["s1"]),
        P("C", "Uranus est la septième planète.", True, "Uranus vient juste après Saturne : septième position.", ["s1"]),
        P("D", "Neptune est la septième planète.", False, "Neptune est la huitième et dernière planète citée ; la septième est Uranus.", ["s1"]),
        P("E", "Trois planètes séparent la Terre de Saturne.", False, "Seules Mars et Jupiter se trouvent entre la Terre et Saturne : deux planètes, pas trois.", ["s1"]),
    ], [S_ORDRE()], explain={
        "text": "Il suffit de numéroter la liste du cours : 1 Mercure, 2 Vénus, 3 la Terre, 4 Mars, 5 Jupiter, 6 Saturne, 7 Uranus, 8 Neptune.",
        "analogy": None, "sourceRefs": ["s1"]}))
    # ---- B. classification (tableau) ----------------------------------------------------------------
    qs.append(Q("n_demo_classification", "qcu", 1, "Laquelle de ces planètes est une planète tellurique ?", [
        P("A", "Jupiter", False, "Jupiter est une géante gazeuse.", ["s1"]),
        P("B", "Mars", True, "Mars fait partie des planètes telluriques citées par le cours : Mercure, Vénus, la Terre et Mars.", ["s2"]),
        P("C", "Saturne", False, "Saturne est une géante gazeuse.", ["s1"]),
        P("D", "Neptune", False, "Neptune est une géante de glaces.", ["s1"]),
    ], [S_GEANTES("s1"), S_TELL("s2")]))
    qs.append(Q("n_demo_classification", "tf", 2, "Vrai ou faux : Uranus et Neptune sont des géantes gazeuses.", [
        P("V", "Vrai", False, "Le cours classe Uranus et Neptune parmi les géantes de glaces, pas parmi les géantes gazeuses.", ["s1"]),
        P("F", "Faux", True, "Les géantes gazeuses sont Jupiter et Saturne ; Uranus et Neptune sont des géantes de glaces.", ["s1"]),
    ], [S_GEANTES("s1")]))
    qs.append(Q("n_demo_classification", "qcm", 3, "D'après le tableau de classification, quelles associations sont exactes ?", [
        P("A", "Telluriques : roches et métaux", True, "La ligne « Telluriques » indique « Roches et métaux ».", ["s1"]),
        P("B", "Géantes gazeuses : hydrogène et hélium", True, "La ligne « Géantes gazeuses » indique « Hydrogène et hélium ».", ["s1"]),
        P("C", "Géantes de glaces : hydrogène et hélium", False, "La ligne « Géantes de glaces » indique des glaces (eau, ammoniac, méthane), pas hydrogène et hélium.", ["s1"]),
        P("D", "Mars : géante de glaces", False, "Mars figure dans la ligne « Telluriques ».", ["s1"]),
        P("E", "La Terre : roches et métaux", True, "La Terre figure dans la ligne « Telluriques », dont la composition est « Roches et métaux ».", ["s1"]),
    ], [table("s1")], review="Réponses tirées d'un tableau : vérifier la lecture des lignes sur la capture."))
    # ---- C. records (abeille) -------------------------------------------------------------------------
    qs.append(Q("n_demo_records", "qcu", 1, "Quelle est la planète la plus chaude du Système solaire ?", [
        P("A", "Mercure", False, "Le cours désigne Vénus comme la planète la plus chaude, pas Mercure.", ["s1"]),
        P("B", "Vénus", True, "Le cours : Vénus est la planète la plus chaude, avec une température de surface d'environ 465 °C.", ["s1"]),
        P("C", "La Terre", False, "La Terre n'est pas citée comme la plus chaude : c'est Vénus.", ["s1"]),
        P("D", "Mars", False, "Mars n'est pas citée comme la plus chaude : c'est Vénus.", ["s1"]),
    ], [S_VENUS("s1")], explain={
        "text": "Le cours cite un record : Vénus est la planète la plus chaude du Système solaire, avec environ 465 °C en surface.",
        "analogy": {"text": "Pense à une étiquette « championne de chaleur » collée sur Vénus.", "label": "hors cours"},
        "sourceRefs": ["s1"]}))
    qs.append(Q("n_demo_records", "tf", 2,
                "Vrai ou faux : Mercure est la planète la plus chaude, car c'est la plus proche du Soleil.", [
        P("V", "Vrai", False, "Le cours désigne Vénus, et non Mercure, comme la planète la plus chaude du Système solaire.", ["s1"]),
        P("F", "Faux", True, "Vénus est la planète la plus chaude (environ 465 °C en surface), pas Mercure.", ["s1"]),
    ], [S_VENUS("s1")]))
    qs.append(Q("n_demo_records", "qcm", 3,
                "Parmi les affirmations suivantes sur les records des planètes, lesquelles sont exactes ?", [
        P("A", "La plus grande planète est aussi la plus chaude.", False, "Jupiter est la plus grande ; la plus chaude est Vénus.", ["s1", "s2"]),
        P("B", "Mercure est la plus petite planète.", True, "Le cours : Mercure est la plus petite.", ["s1"]),
        P("C", "La température de surface de Vénus est d'environ 465 °C.", True, "C'est la valeur donnée par le cours.", ["s2"]),
        P("D", "Vénus est plus chaude que Mercure.", True, "Vénus est la planète la plus chaude : elle est donc plus chaude que Mercure.", ["s2"]),
        P("E", "Mercure est la planète la plus chaude car la plus proche du Soleil.", False, "Le cours désigne Vénus comme la plus chaude.", ["s2"]),
    ], [S_RECORDS("s1"), S_VENUS("s2")]))
    # ---- D. année terrestre -------------------------------------------------------------------------------
    qs.append(Q("n_demo_annee_terrestre", "qcu", 1, "Quelle est la durée approximative de l'année terrestre selon le cours ?", [
        P("A", "Environ 24 heures", False, "24 heures n'est pas la durée d'un tour autour du Soleil : le cours donne environ 365,25 jours.", ["s1"]),
        P("B", "Environ 30 jours", False, "Le cours donne environ 365,25 jours pour un tour autour du Soleil.", ["s1"]),
        P("C", "Environ 365,25 jours", True, "C'est la durée donnée par le cours pour un tour de la Terre autour du Soleil.", ["s1"]),
        P("D", "Environ 687 jours", False, "Le cours donne environ 365,25 jours pour la Terre.", ["s1"]),
    ], [S_ANNEE("s1")]))
    qs.append(Q("n_demo_annee_terrestre", "tf", 2,
                "Vrai ou faux : la Terre met exactement 365 jours pour faire un tour autour du Soleil.", [
        P("V", "Vrai", False, "Le cours indique « environ 365,25 jours », pas exactement 365.", ["s1"]),
        P("F", "Faux", True, "Le cours donne environ 365,25 jours.", ["s1"]),
    ], [S_ANNEE("s1")]))
    # ---- E. axe d'Uranus -------------------------------------------------------------------------------------
    qs.append(Q("n_demo_axe_uranus", "qcu", 1, "De combien l'axe de rotation d'Uranus est-il incliné, d'après le cours ?", [
        P("A", "Environ 23°", False, "Le cours indique environ 98° pour Uranus.", ["s1"]),
        P("B", "Environ 45°", False, "Le cours indique environ 98° pour Uranus.", ["s1"]),
        P("C", "Environ 98°", True, "Le cours : l'axe de rotation d'Uranus est incliné d'environ 98°.", ["s1"]),
        P("D", "Environ 180°", False, "Le cours indique environ 98°, pas 180°.", ["s1"]),
    ], [S_URANUS("s1")]))
    qs.append(Q("n_demo_axe_uranus", "tf", 2, "Vrai ou faux : Uranus tourne pour ainsi dire couchée sur le côté.", [
        P("V", "Vrai", True, "C'est la formulation du cours : son axe est incliné d'environ 98°.", ["s1"]),
        P("F", "Faux", False, "Le cours dit au contraire que la planète tourne pour ainsi dire couchée sur le côté.", ["s1"]),
    ], [S_URANUS("s1")]))
    # ---- F. Kepler -------------------------------------------------------------------------------------------------
    qs.append(Q("n_demo_kepler", "clinical", 2, "Quelle est sa période orbitale, en années ?", [
        P("A", "2 ans", False, "Avec T² = a³ et a = 4, on obtient T² = 64 : T ne peut pas valoir 2 (T² = 4).", ["s1"]),
        P("B", "4 ans", False, "Si T valait 4, T² vaudrait 16, pas 64.", ["s1"]),
        P("C", "8 ans", True, "T² = a³ = 4³ = 64, donc T = 8 années.", ["s1"]),
        P("D", "16 ans", False, "Si T valait 16, T² vaudrait 256, pas 64.", ["s1"]),
        P("E", "64 ans", False, "64 est la valeur de T², pas de T.", ["s1"]),
    ], [formula("s1"), S_KEPLER_TXT("s2")],
        vignette="Un astronome amateur étudie une planète fictive qui orbite autour du Soleil avec un demi-grand axe de 4 UA.",
        explain={"text": "Le cours donne la relation T² = a³ (T en années, a en UA). Avec a = 4 : T² = 4 × 4 × 4 = 64, donc T = 8.",
                 "analogy": None, "sourceRefs": ["s1", "s2"]}))
    qs.append(Q("n_demo_kepler", "qcu", 1, "Quelle relation exprime la troisième loi de Kepler, d'après le cours ?", [
        P("A", "T = a", False, "La relation du cours relie le carré de T au cube de a : T² = a³.", ["s1"]),
        P("B", "T² = a³", True, "C'est la formule encadrée du cours.", ["s1"]),
        P("C", "T³ = a²", False, "Les exposants sont inversés par rapport à la formule du cours.", ["s1"]),
        P("D", "T = a²", False, "La formule du cours est T² = a³, pas T = a².", ["s1"]),
    ], [formula("s1")]))
    return qs


def sheet():
    items = [
        {"kind": "keypoint", "text": "Ordre à partir du Soleil : Mercure, Vénus, la Terre, Mars, Jupiter, Saturne, Uranus, Neptune.",
         "notionId": "n_demo_ordre_planetes", "priority": True, "beeIds": BEE["n_demo_ordre_planetes"], "sources": [S_ORDRE()]},
        {"kind": "number", "text": "Vénus : la plus chaude (environ 465 °C en surface). Jupiter : la plus grande. Mercure : la plus petite.",
         "notionId": "n_demo_records", "priority": True, "beeIds": BEE["n_demo_records"],
         "sources": [S_VENUS("s1"), S_RECORDS("s2")]},
        {"kind": "definition", "text": "Planètes telluriques : Mercure, Vénus, la Terre et Mars, rocheuses, à surface solide.",
         "notionId": "n_demo_classification", "priority": False, "sources": [S_TELL("s1")]},
        {"kind": "classification", "text": "Telluriques : roches et métaux. Géantes gazeuses : hydrogène et hélium. Géantes de glaces : glaces (eau, ammoniac, méthane).",
         "notionId": "n_demo_classification", "priority": False, "sources": [table("s1")]},
        {"kind": "keypoint", "text": "Géantes gazeuses : Jupiter et Saturne. Géantes de glaces : Uranus et Neptune.",
         "notionId": "n_demo_classification", "priority": False, "sources": [S_GEANTES("s1")]},
        {"kind": "number", "text": "Année terrestre : environ 365,25 jours.",
         "notionId": "n_demo_annee_terrestre", "priority": False, "sources": [S_ANNEE("s1")]},
        {"kind": "number", "text": "Axe d'Uranus incliné d'environ 98° : elle tourne couchée sur le côté.",
         "notionId": "n_demo_axe_uranus", "priority": False, "sources": [S_URANUS("s1")]},
        {"kind": "formula", "text": "Troisième loi de Kepler : T² = a³ (T en années, a en UA).",
         "notionId": "n_demo_kepler", "priority": False, "sources": [formula("s1")]},
    ]
    return {"schemaVersion": "1.0.0", "chapterId": CH, "gen": GEN,
            "sheet": {"title": "Les planètes : fiche de synthèse", "items": items}}


def mnemonics():
    planets = ["Mercure", "Vénus", "Terre", "Mars", "Jupiter", "Saturne", "Uranus", "Neptune"]
    tokens = ["Mon", "Vélo", "Transporte", "Mes", "Jolis", "Sacs", "Usés", "Noirs"]
    return {"schemaVersion": "1.0.0", "chapterId": CH, "gen": GEN, "mnemonics": [{
        "notionId": "n_demo_ordre_planetes",
        "title": "Les huit planètes, dans l'ordre à partir du Soleil",
        "list": {"ordered": True, "items": [{"text": p} for p in planets]},
        "sources": [S_ORDRE()],
        "mnemonic": {"kind": "phrase", "text": " ".join(tokens),
                     "mapping": [{"token": t, "itemIndex": i} for i, t in enumerate(tokens)]},
    }]}


def taxonomy():
    def ref(page, section):
        return {"sourceId": SRC, "page": page, "section": section}
    notions = [
        {"id": "n_demo_ordre_planetes", "title": "Ordre des planètes à partir du Soleil", "priority": True,
         "beeIds": BEE["n_demo_ordre_planetes"], "refs": [ref(1, "1. Vue d'ensemble")]},
        {"id": "n_demo_classification", "title": "Planètes telluriques et géantes", "priority": False, "beeIds": [],
         "refs": [ref(1, "2. Classification des planètes"), ref(2, "3. Les planètes géantes")]},
        {"id": "n_demo_records", "title": "Records des planètes", "priority": True,
         "beeIds": BEE["n_demo_records"], "refs": [ref(2, "4. Quelques records")]},
        {"id": "n_demo_annee_terrestre", "title": "Durée de l'année terrestre", "priority": False, "beeIds": [],
         "refs": [ref(3, "5. Mouvements des planètes")]},
        {"id": "n_demo_axe_uranus", "title": "Inclinaison de l'axe d'Uranus", "priority": False, "beeIds": [],
         "refs": [ref(3, "5. Mouvements des planètes")]},
        {"id": "n_demo_kepler", "title": "Troisième loi de Kepler", "priority": False, "beeIds": [],
         "refs": [ref(3, "6. Troisième loi de Kepler")]},
    ]
    return {"schemaVersion": "1.0.0", "years": [{
        "id": "y_demo", "code": "DEMO", "label": "Démo (non médical)",
        "ues": [{"id": "ue_demo_astro", "code": "UE D1", "title": "Astronomie", "semester": "S1", "modules": [{
            "id": "mod_demo_systeme_solaire", "title": "Le Système solaire",
            "chapters": [{"id": CH, "title": "Les planètes", "sourceIds": [SRC], "tier": "incontournable",
                          "beeCount": 2, "notions": notions}]}]}]}]}


def dump(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    dump(CONTENT / "taxonomy.json", taxonomy())
    chapter = CONTENT / "chapters" / CH
    dump(chapter / "questions.json", {"schemaVersion": "1.0.0", "chapterId": CH, "gen": GEN, "questions": questions()})
    dump(chapter / "sheet.json", sheet())
    dump(chapter / "mnemonics.json", mnemonics())
    print(f"écrit dans {CONTENT} : {len(questions())} questions, 1 fiche, 1 mnémotechnique")


if __name__ == "__main__":
    main()
