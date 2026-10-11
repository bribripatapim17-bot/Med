"""Le validateur doit laisser passer le contenu de démo et refuser chaque triche ou incohérence connue."""
import json
import shutil
from pathlib import Path

import pytest

from quizpipe.validate import Config, stamp_content, validate_content

DEMO = Path(__file__).resolve().parents[2] / "demo"
CFG = Config(min_questions_normal=2, min_questions_bee=3)
CH = "chapters/ch_demo_planetes"


@pytest.fixture()
def ws(tmp_path):
    shutil.copytree(DEMO / "content", tmp_path / "content")
    shutil.copytree(DEMO / "work", tmp_path / "work")
    stamp_content(tmp_path / "content", tmp_path / "work")
    return tmp_path


def edit(ws: Path, rel: str, fn) -> None:
    p = ws / "content" / rel
    data = json.loads(p.read_text(encoding="utf-8"))
    fn(data)
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def run(ws: Path, stage: str = "generated"):
    return validate_content(ws / "content", ws / "work", stage, CFG)


def codes(report, severity: str = "error") -> set[str]:
    return {i.code for i in report.issues if i.severity == severity}


def q(data, i):
    return data["questions"][i]


# --------------------------------------------------------------------------- contenu sain

def test_demo_has_no_error(ws):
    r = run(ws)
    assert r.errors == [], "\n".join(map(str, r.errors))
    assert r.stats["questions : total"] == 16
    assert r.stats["notions abeille"] == 2
    assert r.stats["chapitres incontournables"] == 1


def test_ambiguous_bee_is_reported_not_guessed(ws):
    r = run(ws)
    assert r.ambiguous_bees == ["bee_demo_planetes_p3_01"]
    assert r.stats["abeilles rattachées"] == 2


def test_typography_differences_are_tolerated(ws):
    edit(ws, f"{CH}/questions.json", lambda d: q(d, 0)["sources"][0].update(
        excerpt="Dans l’ordre à partir du Soleil : Mercure, Vénus, la Terre, Mars, Jupiter, Saturne, Uranus et Neptune."))
    assert "E-QUOTE" not in codes(run(ws))


# --------------------------------------------------------------------------- traçabilité

def test_invented_excerpt_is_rejected(ws):
    edit(ws, f"{CH}/questions.json", lambda d: q(d, 0)["sources"][0].update(
        excerpt="Mercure est la planète la plus proche du Soleil, à environ 58 millions de kilomètres."))
    assert "E-QUOTE" in codes(run(ws))


def test_altered_number_is_rejected(ws):
    edit(ws, f"{CH}/questions.json", lambda d: q(d, 7)["sources"][0].update(
        excerpt="Vénus est la planète la plus chaude du Système solaire, avec une température de surface d'environ 475 °C."))
    assert "E-QUOTE" in codes(run(ws))


def test_excerpt_on_wrong_page_is_rejected(ws):
    edit(ws, f"{CH}/questions.json", lambda d: q(d, 0)["sources"][0].update(page=2))
    assert "E-QUOTE" in codes(run(ws))


def test_page_out_of_document(ws):
    edit(ws, f"{CH}/questions.json", lambda d: q(d, 0)["sources"][0].update(page=9))
    assert "E-PAGE" in codes(run(ws))


def test_missing_extracted_text_is_reported_once(ws):
    (ws / "work" / "pages" / "src_demo_planetes.pages.json").unlink()
    r = run(ws)
    assert [i.code for i in r.errors].count("E-PAGES-MISSING") == 1


def test_every_proposition_needs_its_own_explanation_and_source(ws):
    edit(ws, f"{CH}/questions.json", lambda d: q(d, 1)["propositions"][2].pop("explanation"))
    assert "E-SCHEMA" in codes(run(ws))
    edit(ws, f"{CH}/questions.json", lambda d: q(d, 1)["propositions"][2].update(explanation="Faux.", sourceRefs=[]))
    assert "E-SCHEMA" in codes(run(ws))


def test_unknown_citation_label(ws):
    edit(ws, f"{CH}/questions.json", lambda d: q(d, 0)["propositions"][0].update(sourceRefs=["s9"]))
    assert "E-REF" in codes(run(ws))


def test_figure_without_alt_text_is_refused(ws):
    edit(ws, f"{CH}/questions.json", lambda d: q(d, 6)["sources"][0].pop("alt"))
    assert "E-SCHEMA" in codes(run(ws))


def test_needs_review_requires_a_reason(ws):
    edit(ws, f"{CH}/questions.json", lambda d: q(d, 6).update(verify={"needsReview": True}))
    assert "E-SCHEMA" in codes(run(ws))


def test_stale_course_is_flagged(ws):
    edit(ws, f"{CH}/questions.json", lambda d: d["gen"].update(sourceHash="0" * 64))
    assert "W-STALE" in codes(run(ws), "warning")


# --------------------------------------------------------------------------- forme des questions

def test_true_false_shape(ws):
    edit(ws, f"{CH}/questions.json", lambda d: [p.update(correct=True) for p in q(d, 2)["propositions"]])
    assert "E-ANSWER" in codes(run(ws))


def test_qcu_needs_exactly_one_correct_answer(ws):
    edit(ws, f"{CH}/questions.json", lambda d: q(d, 0)["propositions"][1].update(correct=True))
    assert "E-ANSWER" in codes(run(ws))


def test_qcm_must_be_multiple_mode(ws):
    edit(ws, f"{CH}/questions.json", lambda d: q(d, 1).update(answerMode="single"))
    assert "E-ANSWER" in codes(run(ws))


def test_clinical_case_requires_vignette(ws):
    edit(ws, f"{CH}/questions.json", lambda d: q(d, 14).pop("vignette"))
    assert "E-SCHEMA" in codes(run(ws))


def test_exact_duplicate_is_rejected(ws):
    edit(ws, f"{CH}/questions.json", lambda d: d["questions"].append(json.loads(json.dumps(q(d, 0)))))
    assert "E-DUP" in codes(run(ws))


def test_unknown_notion(ws):
    edit(ws, f"{CH}/questions.json", lambda d: q(d, 0).update(notionId="n_demo_inconnue"))
    assert "E-REF" in codes(run(ws))


# --------------------------------------------------------------------------- abeilles

def test_bee_notion_questions_must_carry_the_badge(ws):
    edit(ws, f"{CH}/questions.json", lambda d: q(d, 0).update(priority=False, beeIds=[]))
    assert "E-PRIORITY" in codes(run(ws))


def test_badge_without_bee_is_refused(ws):
    edit(ws, f"{CH}/questions.json", lambda d: q(d, 4).update(priority=True, beeIds=["bee_demo_planetes_p1_01"]))
    assert "E-PRIORITY" in codes(run(ws))


def test_chapter_tier_follows_bee_count(ws):
    edit(ws, "taxonomy.json", lambda d: d["years"][0]["ues"][0]["modules"][0]["chapters"][0].update(tier="standard"))
    assert "E-BEE-TIER" in codes(run(ws))


def test_notion_must_list_its_bees(ws):
    edit(ws, "taxonomy.json", lambda d: d["years"][0]["ues"][0]["modules"][0]["chapters"][0]["notions"][0].update(beeIds=[]))
    assert "E-BEE-LINK" in codes(run(ws))


def test_attached_bee_anchor_must_exist_on_page(ws):
    def mutate(d):
        d["bees"][0]["attachment"]["anchor"]["text"] = "Phrase qui n'existe pas dans le cours."
    edit(ws, "bees.json", mutate)
    assert "E-QUOTE" in codes(run(ws))


# --------------------------------------------------------------------------- fiche

def test_sheet_must_feature_every_bee_notion(ws):
    edit(ws, f"{CH}/sheet.json", lambda d: d["sheet"]["items"].pop(1))
    assert "E-SHEET" in codes(run(ws))


def test_sheet_must_fit_one_page(ws):
    def mutate(d):
        for it in d["sheet"]["items"]:
            it["text"] = "a" * 300
    edit(ws, f"{CH}/sheet.json", mutate)
    assert "E-SHEET" in codes(run(ws))


# --------------------------------------------------------------------------- mnémotechniques

def mn(d):
    return d["mnemonics"][0]


def test_mnemonic_in_wrong_order(ws):
    def mutate(d):
        m = mn(d)["mnemonic"]["mapping"]
        m[1]["itemIndex"], m[2]["itemIndex"] = 2, 1
    edit(ws, f"{CH}/mnemonics.json", mutate)
    assert "E-MNEMO" in codes(run(ws))


def test_mnemonic_with_wrong_initial(ws):
    def mutate(d):
        mn(d)["mnemonic"]["mapping"][1]["token"] = "Chat"
        mn(d)["mnemonic"]["text"] = mn(d)["mnemonic"]["text"].replace("Vélo", "Chat")
    edit(ws, f"{CH}/mnemonics.json", mutate)
    assert "E-MNEMO" in codes(run(ws))


def test_mnemonic_that_adds_a_word(ws):
    edit(ws, f"{CH}/mnemonics.json", lambda d: mn(d)["mnemonic"].update(text="Mon Vélo Transporte Mes Jolis Sacs Usés Noirs et Lourds"))
    assert "E-MNEMO" in codes(run(ws))


def test_mnemonic_list_must_be_the_course_list(ws):
    def mutate(d):
        mn(d)["list"]["items"].append({"text": "Pluton"})
        mn(d)["mnemonic"]["mapping"].append({"token": "Pas", "itemIndex": 8})
        mn(d)["mnemonic"]["text"] += " Pas"
    edit(ws, f"{CH}/mnemonics.json", mutate)
    assert "E-MNEMO" in codes(run(ws))


def test_mnemonic_that_omits_an_item(ws):
    def mutate(d):
        mn(d)["mnemonic"]["mapping"].pop()
        mn(d)["mnemonic"]["text"] = "Mon Vélo Transporte Mes Jolis Sacs Usés"
    edit(ws, f"{CH}/mnemonics.json", mutate)
    assert "E-MNEMO" in codes(run(ws))


# --------------------------------------------------------------------------- étape build

def test_built_stage_demands_ids_hashes_and_verification(ws):
    r = run(ws, "built")
    assert "E-SCHEMA" in codes(r)
    messages = " ".join(i.message for i in r.errors)
    for field in ("'id'", "'hash'", "'widgetFriendly'", "'verification'"):
        assert f"{field} is a required property" in messages, field
