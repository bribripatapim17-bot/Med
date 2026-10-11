"""Validation du contenu : schéma JSON + règles sémantiques (traçabilité, abeilles, QCM, mnémotechniques).

Erreurs (bloquent le build) :
  E-FILE E-JSON E-SCHEMA     fichier manquant, JSON invalide, non conforme au schéma
  E-REF E-PAGE E-ID-DUP      référence inconnue, page hors document, identifiant en double
  E-QUOTE                    extrait « Dans le cours » introuvable tel quel sur la page citée
  E-PAGES-MISSING            texte des pages absent (étape extract non lancée)
  E-ANSWER                   forme de la question incohérente (type, mode, bonnes réponses, ids)
  E-PRIORITY E-BEE-*         incohérence abeille / notion / question / chapitre
  E-DUP                      question en double (même énoncé et mêmes propositions)
  E-SHEET E-MNEMO            fiche ou mnémotechnique non conforme
  E-HASH E-MANIFEST E-IMAGE  contrôles de l'étape built
Avertissements (à relire) :
  W-SECTION W-IMAGE-REGION W-SRC-UNUSED W-REF-SOURCE W-STALE (cours modifié depuis la génération)
  W-DUP-NEAR W-COVER-EMPTY W-COVER-DIFF W-COVER-QUOTA W-BEE-AMBIGUOUS W-NO-SHEET W-SHEET-ORDER W-ANSWER
"""
from __future__ import annotations

import copy
import difflib
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from .textnorm import excerpt_in_page, find_in_order, fold, normalize, page_variants, sha256_text, split_excerpt

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "content.schema.json"
BEE_OK = ("attached", "validated")

PACK_DEFS = {
    "taxonomy": "Taxonomy", "sources": "SourcesPack", "bees": "BeesPack",
    "questions": "QuestionsPack", "sheet": "SheetPack", "mnemonics": "MnemonicsPack",
    "manifest": "Manifest", "index": "QuestionIndex",
}


# --------------------------------------------------------------------------- rapport

@dataclass(frozen=True)
class Issue:
    severity: str  # "error" | "warning"
    code: str
    where: str
    message: str

    def __str__(self) -> str:
        tag = "ERREUR" if self.severity == "error" else "avert."
        return f"{tag:<6} {self.code:<15} {self.where} : {self.message}"


@dataclass
class Config:
    min_questions_normal: int = 3   # par notion standard : une question par niveau de difficulté
    min_questions_bee: int = 6      # par notion abeille : deux par niveau
    sheet_max_chars: int = 1800     # « une page maximum »
    near_dup_ratio: float = 0.88


@dataclass
class Report:
    issues: list[Issue] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)
    ambiguous_bees: list[str] = field(default_factory=list)

    def error(self, code: str, where: str, message: str) -> None:
        self.issues.append(Issue("error", code, where, message))

    def warn(self, code: str, where: str, message: str) -> None:
        self.issues.append(Issue("warning", code, where, message))

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def codes(self) -> set[str]:
        return {i.code for i in self.issues}

    def render_markdown(self, title: str = "Rapport de validation") -> str:
        verdict = "ÉCHEC" if self.errors else "OK"
        out = [f"# {title}", "", f"**Résultat : {verdict}** - {len(self.errors)} erreur(s), "
               f"{len(self.warnings)} avertissement(s)", ""]
        if self.stats:
            out += ["## Chiffres", "", "| Mesure | Valeur |", "|---|---|"]
            out += [f"| {k} | {v} |" for k, v in self.stats.items()]
            out.append("")
        for label, items in (("Erreurs", self.errors), ("Avertissements", self.warnings)):
            if items:
                out += [f"## {label}", ""] + [f"- `{i.code}` {i.where} : {i.message}" for i in items] + [""]
        if self.ambiguous_bees:
            out += ["## Abeilles ambiguës à valider", ""] + [f"- {b}" for b in self.ambiguous_bees] + [""]
        return "\n".join(out)


# --------------------------------------------------------------------------- schéma

_schema_cache: dict | None = None


def load_schema() -> dict:
    global _schema_cache
    if _schema_cache is None:
        _schema_cache = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return _schema_cache


def schema_for(pack_kind: str, stage: str = "generated") -> dict:
    """Schéma d'un pack. stage="built" rend obligatoires les champs ajoutés par build (x-builtRequired)."""
    root = copy.deepcopy(load_schema())
    if stage == "built":
        for d in root["$defs"].values():
            extra = d.get("x-builtRequired")
            if extra:
                d["required"] = sorted(set(d.get("required", [])) | set(extra))
    return {"$schema": root["$schema"], "$ref": f"#/$defs/{PACK_DEFS[pack_kind]}", "$defs": root["$defs"]}


def schema_issues(kind: str, data, stage: str, where: str) -> list[Issue]:
    validator = Draft202012Validator(schema_for(kind, stage), format_checker=FormatChecker())
    out = []
    for err in sorted(validator.iter_errors(data), key=lambda e: [str(p) for p in e.absolute_path]):
        path = "/".join(str(p) for p in err.absolute_path) or "(racine)"
        out.append(Issue("error", "E-SCHEMA", f"{where}#{path}", err.message[:300]))
    return out


# --------------------------------------------------------------------------- contexte

class PageIndex:
    """Texte des pages extraites (work/pages/<sourceId>.pages.json), prêt pour la recherche d'extraits."""

    def __init__(self, pages_dir: Path):
        self.dir = pages_dir
        self._docs: dict[str, dict | None] = {}
        self._variants: dict[tuple[str, int], list[str]] = {}

    def doc(self, source_id: str) -> dict | None:
        if source_id not in self._docs:
            p = self.dir / f"{source_id}.pages.json"
            self._docs[source_id] = json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
        return self._docs[source_id]

    def page(self, source_id: str, page_no: int) -> dict | None:
        d = self.doc(source_id)
        if d is None or not (1 <= page_no <= len(d["pages"])):
            return None
        return d["pages"][page_no - 1]

    def variants(self, source_id: str, page_no: int) -> list[str]:
        key = (source_id, page_no)
        if key not in self._variants:
            pg = self.page(source_id, page_no)
            self._variants[key] = page_variants(pg["text"]) if pg else []
        return self._variants[key]


@dataclass
class Context:
    cfg: Config
    report: Report
    stage: str
    pages: PageIndex
    content: Path
    sources: dict[str, dict] = field(default_factory=dict)
    bees: dict[str, dict] = field(default_factory=dict)
    chapters: dict[str, dict] = field(default_factory=dict)
    notions: dict[str, tuple[str, dict]] = field(default_factory=dict)
    seen_ids: dict[str, str] = field(default_factory=dict)
    seen_hash: dict[str, str] = field(default_factory=dict)
    missing_pages: set[str] = field(default_factory=set)


def _claim(ctx: Context, id_: str | None, where: str) -> None:
    if id_ is None:
        return
    if id_ in ctx.seen_ids:
        ctx.report.error("E-ID-DUP", where, f"identifiant déjà utilisé ({ctx.seen_ids[id_]}) : {id_}")
    else:
        ctx.seen_ids[id_] = where


def _overlap_ratio(a: list[float], b: list[float]) -> float:
    """Part de la surface de b couverte par a (boîtes [x, y, w, h])."""
    ix = max(0.0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
    area = b[2] * b[3]
    return (ix * iy) / area if area > 0 else 0.0


def chapter_source_hash(pages: PageIndex, source_ids: list[str]) -> str | None:
    """Empreinte du texte des sources d'un chapitre ; change si un cours est modifié."""
    parts: list[str] = []
    for sid in sorted(source_ids):
        doc = pages.doc(sid)
        if doc is None:
            return None
        parts.append(sid)
        parts.extend(normalize(p["text"]) for p in doc["pages"])
    return sha256_text("\n".join(parts))


def check_stale(pack: dict, chapter_id: str, where: str, ctx: Context) -> None:
    stamped = pack.get("gen", {}).get("sourceHash")
    if stamped is None:
        return
    current = chapter_source_hash(ctx.pages, ctx.chapters[chapter_id]["sourceIds"])
    if current is not None and current != stamped:
        ctx.report.warn("W-STALE", where, "le cours a changé depuis la génération : régénérer ce chapitre")


# --------------------------------------------------------------------------- citations « Dans le cours »

def check_source_ref(ref: dict, where: str, ctx: Context) -> None:
    r = ctx.report
    sid, page_no = ref["sourceId"], ref["page"]
    src = ctx.sources.get(sid)
    if src is None:
        r.error("E-REF", where, f"source inconnue : {sid}")
        return
    if page_no > src["pageCount"]:
        r.error("E-PAGE", where, f"page {page_no} hors du document ({src['pageCount']} pages) : {src['fileName']}")
        return
    pg = ctx.pages.page(sid, page_no)
    if pg is None:
        if sid not in ctx.missing_pages:
            ctx.missing_pages.add(sid)
            r.error("E-PAGES-MISSING", sid, "texte des pages introuvable : lancer `quizpipe extract` pour cette source")
        return
    excerpt = ref.get("excerpt")
    if excerpt is not None and not excerpt_in_page(excerpt, ctx.pages.variants(sid, page_no)):
        r.error("E-QUOTE", where, f"extrait introuvable tel quel p.{page_no} de {src['fileName']} : "
                                  f"« {excerpt[:90]}{'...' if len(excerpt) > 90 else ''} »")
    section = ref.get("section")
    if section and fold(normalize(section)) not in fold(ctx.pages.variants(sid, page_no)[0]):
        r.warn("W-SECTION", where, f"section « {section} » introuvable sur la page {page_no}")
    image = ref.get("image")
    if image:
        if ref["kind"] == "table" and pg["tables"]:
            if max(_overlap_ratio(image["bbox"], t["bbox"]) for t in pg["tables"]) < 0.5:
                r.warn("W-IMAGE-REGION", where, "la capture ne couvre pas le tableau détecté sur la page")
        elif ref["kind"] == "figure" and pg["images"]:
            if max(_overlap_ratio(image["bbox"], i["bbox"]) for i in pg["images"]) < 0.5:
                r.warn("W-IMAGE-REGION", where, "la capture ne couvre pas l'image détectée sur la page")
        if ctx.stage == "built":
            path = image.get("path")
            if not path or not (ctx.content / path).exists():
                r.error("E-IMAGE", where, f"capture absente du pack : {path}")


# --------------------------------------------------------------------------- taxonomie et abeilles

def check_taxonomy(tax: dict, ctx: Context) -> None:
    r = ctx.report
    linked_by_notion: dict[str, list[str]] = defaultdict(list)
    for b in ctx.bees.values():
        a = b["attachment"]
        if a["status"] in BEE_OK and "notionId" in a:
            linked_by_notion[a["notionId"]].append(b["id"])
    for y in tax["years"]:
        _claim(ctx, y["id"], f"taxonomy#{y['id']}")
        for ue in y["ues"]:
            _claim(ctx, ue["id"], f"taxonomy#{ue['id']}")
            for m in ue["modules"]:
                _claim(ctx, m["id"], f"taxonomy#{m['id']}")
                for c in m["chapters"]:
                    where = f"taxonomy#{c['id']}"
                    _claim(ctx, c["id"], where)
                    ctx.chapters[c["id"]] = c
                    for sid in c["sourceIds"]:
                        if sid not in ctx.sources:
                            r.error("E-REF", where, f"source inconnue : {sid}")
                    bee_total = 0
                    for n in c["notions"]:
                        nwhere = f"taxonomy#{n['id']}"
                        _claim(ctx, n["id"], nwhere)
                        ctx.notions[n["id"]] = (c["id"], n)
                        linked = sorted(linked_by_notion.get(n["id"], []))
                        if sorted(n["beeIds"]) != linked:
                            r.error("E-BEE-LINK", nwhere, f"beeIds {sorted(n['beeIds'])} différent des abeilles rattachées {linked}")
                        if n["priority"] != bool(linked):
                            r.error("E-PRIORITY", nwhere, "priority doit valoir true si et seulement si une abeille est rattachée")
                        for ref in n["refs"]:
                            src = ctx.sources.get(ref["sourceId"])
                            if src is None:
                                r.error("E-REF", nwhere, f"source inconnue : {ref['sourceId']}")
                            elif ref["page"] > src["pageCount"]:
                                r.error("E-PAGE", nwhere, f"page {ref['page']} hors du document")
                        bee_total += len(linked)
                    if c["beeCount"] != bee_total:
                        r.error("E-BEE-COUNT", where, f"beeCount={c['beeCount']} mais {bee_total} abeille(s) rattachée(s)")
                    tier = "incontournable" if bee_total >= 2 else "standard"
                    if c["tier"] != tier:
                        r.error("E-BEE-TIER", where, f"tier={c['tier']} mais {bee_total} abeille(s) => {tier}")


def check_bees(ctx: Context) -> None:
    r = ctx.report
    for b in ctx.bees.values():
        where = f"bees#{b['id']}"
        src = ctx.sources.get(b["sourceId"])
        if src is None:
            r.error("E-REF", where, f"source inconnue : {b['sourceId']}")
            continue
        if b["page"] > src["pageCount"]:
            r.error("E-PAGE", where, f"page {b['page']} hors du document")
            continue
        a = b["attachment"]
        if a["status"] in BEE_OK:
            if "notionId" not in a or "anchor" not in a:
                r.error("E-BEE-LINK", where, f"statut {a['status']} : notionId et anchor obligatoires")
                continue
            if a["notionId"] not in ctx.notions:
                r.error("E-REF", where, f"notion inconnue : {a['notionId']}")
            text = a["anchor"].get("text")
            if text and ctx.pages.page(b["sourceId"], b["page"]) and \
                    not excerpt_in_page(text, ctx.pages.variants(b["sourceId"], b["page"])):
                r.error("E-QUOTE", where, f"passage marqué introuvable sur la page : « {text[:80]} »")
        elif a["status"] == "ambiguous":
            r.ambiguous_bees.append(b["id"])
            if not a.get("candidates"):
                r.warn("W-BEE-AMBIGUOUS", where, "abeille ambiguë sans candidat proposé")


# --------------------------------------------------------------------------- questions

def question_hash(q: dict) -> str:
    base = "|".join([normalize(q["stem"]), normalize(q.get("vignette", "")),
                     *sorted(normalize(p["text"]) for p in q["propositions"])])
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def _check_answer_shape(q: dict, where: str, r: Report) -> None:
    props, t, mode = q["propositions"], q["type"], q["answerMode"]
    ids = [p["id"] for p in props]
    n_correct = sum(1 for p in props if p["correct"])
    if t == "tf":
        if ids != ["V", "F"]:
            r.error("E-ANSWER", where, "vrai/faux : propositions V puis F attendues")
        if mode != "single" or n_correct != 1:
            r.error("E-ANSWER", where, "vrai/faux : mode single et une seule bonne réponse attendus")
        return
    if ids != list("ABCDE")[:len(props)]:
        r.error("E-ANSWER", where, f"propositions A, B, C... consécutives attendues, reçu {ids}")
    if t == "qcu" and mode != "single":
        r.error("E-ANSWER", where, "QCU : answerMode doit valoir single")
    if t == "qcm" and mode != "multiple":
        r.error("E-ANSWER", where, "QCM : answerMode doit valoir multiple")
    if mode == "single" and n_correct != 1:
        r.error("E-ANSWER", where, f"mode single : une seule bonne réponse attendue, {n_correct} trouvée(s)")
    if mode == "multiple" and n_correct < 1:
        r.error("E-ANSWER", where, "mode multiple : au moins une bonne réponse attendue")
    if len(props) < 4:
        r.warn("W-ANSWER", where, f"seulement {len(props)} propositions (4 ou 5 attendues pour un QCM/QCU)")


def _check_priority(q: dict, where: str, ctx: Context) -> None:
    r = ctx.report
    chapter_id, notion = ctx.notions[q["notionId"]]
    bee_ids = set(q.get("beeIds", []))
    if q["priority"]:
        if not notion["priority"]:
            r.error("E-PRIORITY", where, "question prioritaire sur une notion sans abeille")
        if not bee_ids:
            r.error("E-PRIORITY", where, "priority=true : beeIds ne peut pas être vide")
        if not bee_ids <= set(notion["beeIds"]):
            r.error("E-PRIORITY", where, f"beeIds {sorted(bee_ids - set(notion['beeIds']))} absentes de la notion")
    elif notion["priority"]:
        r.error("E-PRIORITY", where, "notion abeille : la question doit porter le badge (priority=true)")
    elif bee_ids:
        r.error("E-PRIORITY", where, "beeIds renseigné alors que priority=false")


def check_questions(pack: dict, chapter_id: str, ctx: Context) -> None:
    r = ctx.report
    pack_where = f"chapters/{chapter_id}/questions.json"
    if pack["chapterId"] != chapter_id:
        r.error("E-REF", pack_where, f"chapterId={pack['chapterId']} différent du dossier")
    check_stale(pack, chapter_id, pack_where, ctx)
    per_notion: dict[str, list[dict]] = defaultdict(list)
    for i, q in enumerate(pack["questions"]):
        where = f"{pack_where}#questions[{i}]" + (f"({q['id']})" if "id" in q else "")
        _claim(ctx, q.get("id"), where)
        if q["chapterId"] != chapter_id:
            r.error("E-REF", where, f"chapterId={q['chapterId']} différent du chapitre")
        if q["notionId"] not in ctx.notions:
            r.error("E-REF", where, f"notion inconnue : {q['notionId']}")
            continue
        if ctx.notions[q["notionId"]][0] != chapter_id:
            r.error("E-REF", where, f"la notion {q['notionId']} n'appartient pas au chapitre {chapter_id}")
            continue
        per_notion[q["notionId"]].append(q)

        _check_answer_shape(q, where, r)
        _check_priority(q, where, ctx)

        labels = [s["id"] for s in q["sources"]]
        if len(labels) != len(set(labels)):
            r.error("E-ID-DUP", where, f"étiquettes de citation en double : {labels}")
        used: set[str] = set()
        for p in q["propositions"]:
            for lab in p["sourceRefs"]:
                used.add(lab)
                if lab not in labels:
                    r.error("E-REF", f"{where}.{p['id']}", f"citation inconnue : {lab}")
        for lab in q.get("explain", {}).get("sourceRefs", []):
            used.add(lab)
            if lab not in labels:
                r.error("E-REF", f"{where}.explain", f"citation inconnue : {lab}")
        for lab in sorted(set(labels) - used):
            r.warn("W-SRC-UNUSED", where, f"citation {lab} jamais utilisée")
        chapter_sources = set(ctx.chapters[chapter_id]["sourceIds"])
        for s in q["sources"]:
            check_source_ref(s, f"{where}.{s['id']}", ctx)
            if s["sourceId"] not in chapter_sources:
                r.warn("W-REF-SOURCE", f"{where}.{s['id']}", f"source {s['sourceId']} hors du chapitre")

        h = question_hash(q)
        if ctx.stage == "built" and q.get("hash") != h:
            r.error("E-HASH", where, "hash absent ou différent du hash recalculé")
        if h in ctx.seen_hash:
            r.error("E-DUP", where, f"doublon exact de {ctx.seen_hash[h]}")
        else:
            ctx.seen_hash[h] = where

    for nid, qs in per_notion.items():
        # Un énoncé générique (« lesquelles sont exactes ? ») est normal en QCM : on compare énoncé + propositions.
        sigs = [normalize(q["stem"]) + " || " + " | ".join(sorted(normalize(p["text"]) for p in q["propositions"]))
                for q in qs]
        for a in range(len(qs)):
            for b in range(a + 1, len(qs)):
                sm = difflib.SequenceMatcher(None, sigs[a], sigs[b])
                if sm.real_quick_ratio() >= ctx.cfg.near_dup_ratio and sm.ratio() >= ctx.cfg.near_dup_ratio:
                    r.warn("W-DUP-NEAR", pack_where, f"questions quasi identiques sur {nid} : "
                                                     f"« {normalize(qs[a]['stem'])[:60]} » / « {normalize(qs[b]['stem'])[:60]} »")

    for nid, (cid, notion) in ctx.notions.items():
        if cid != chapter_id:
            continue
        qs = per_notion.get(nid, [])
        if not qs:
            r.warn("W-COVER-EMPTY", nid, "aucune question sur cette notion")
            continue
        levels = Counter(q["difficulty"] for q in qs)
        missing = [d for d in (1, 2, 3) if levels[d] == 0]
        if missing:
            r.warn("W-COVER-DIFF", nid, f"niveau(x) de difficulté sans question : {missing}")
        quota = ctx.cfg.min_questions_bee if notion["priority"] else ctx.cfg.min_questions_normal
        if len(qs) < quota:
            kind = "abeille" if notion["priority"] else "standard"
            r.warn("W-COVER-QUOTA", nid, f"{len(qs)} question(s), minimum {quota} pour une notion {kind}")


# --------------------------------------------------------------------------- fiches

def check_sheet(pack: dict, chapter_id: str, ctx: Context) -> None:
    r = ctx.report
    where = f"chapters/{chapter_id}/sheet.json"
    if pack["chapterId"] != chapter_id:
        r.error("E-REF", where, f"chapterId={pack['chapterId']} différent du dossier")
    check_stale(pack, chapter_id, where, ctx)
    sheet = pack["sheet"]
    _claim(ctx, sheet.get("id"), where)
    items = sheet["items"]
    total = sum(len(it["text"]) for it in items)
    if total > ctx.cfg.sheet_max_chars:
        r.error("E-SHEET", where, f"{total} caractères : dépasse la page ({ctx.cfg.sheet_max_chars} max)")
    chapter = ctx.chapters[chapter_id]
    covered: set[str] = set()
    seen_plain = False
    for i, it in enumerate(items):
        iw = f"{where}#items[{i}]"
        _claim(ctx, it.get("id"), iw)
        nid = it.get("notionId")
        if nid is not None and (nid not in ctx.notions or ctx.notions[nid][0] != chapter_id):
            r.error("E-REF", iw, f"notion inconnue ou hors chapitre : {nid}")
            nid = None
        if it["priority"]:
            if nid is None:
                r.error("E-SHEET", iw, "item prioritaire sans notionId valide")
            else:
                notion = ctx.notions[nid][1]
                if not notion["priority"]:
                    r.error("E-PRIORITY", iw, "item prioritaire sur une notion sans abeille")
                if not set(it.get("beeIds", [])) <= set(notion["beeIds"]) or not it.get("beeIds"):
                    r.error("E-PRIORITY", iw, "beeIds absent ou étranger à la notion")
                covered.add(nid)
            if seen_plain:
                r.warn("W-SHEET-ORDER", iw, "item abeille placé après des items standard (à mettre en avant en tête)")
        else:
            seen_plain = True
            if nid is not None and ctx.notions[nid][1]["priority"]:
                r.error("E-PRIORITY", iw, "notion abeille : l'item doit être prioritaire")
        for k, s in enumerate(it["sources"]):
            check_source_ref(s, f"{iw}.sources[{k}]", ctx)
    for n in chapter["notions"]:
        if n["priority"] and n["id"] not in covered:
            r.error("E-SHEET", where, f"notion abeille absente de la fiche : {n['id']}")


# --------------------------------------------------------------------------- mnémotechniques

def check_mnemonics(pack: dict, chapter_id: str, ctx: Context) -> None:
    r = ctx.report
    pack_where = f"chapters/{chapter_id}/mnemonics.json"
    if pack["chapterId"] != chapter_id:
        r.error("E-REF", pack_where, f"chapterId={pack['chapterId']} différent du dossier")
    check_stale(pack, chapter_id, pack_where, ctx)
    for i, m in enumerate(pack["mnemonics"]):
        where = f"{pack_where}#mnemonics[{i}]"
        _claim(ctx, m.get("id"), where)
        nid = m["notionId"]
        if nid not in ctx.notions or ctx.notions[nid][0] != chapter_id:
            r.error("E-REF", where, f"notion inconnue ou hors chapitre : {nid}")
        for k, s in enumerate(m["sources"]):
            check_source_ref(s, f"{where}.sources[{k}]", ctx)

        items = [it["text"] for it in m["list"]["items"]]
        n = len(items)
        ordered = m["list"]["ordered"]
        # 1) la liste enregistrée est bien celle du cours, dans l'ordre du cours
        found = False
        for s in m["sources"]:
            if s["kind"] == "text":
                hay = " ".join(split_excerpt(s["excerpt"]))
            else:
                pg = ctx.pages.page(s["sourceId"], s["page"])
                hay = pg["text"] if pg else ""
            if ordered:
                found = found or find_in_order(items, hay)
            else:
                found = found or all(normalize(x) in normalize(hay) for x in items)
        if not found:
            r.error("E-MNEMO", where, "la liste n'apparaît pas telle quelle (ni dans l'ordre) dans l'extrait du cours cité")
        # 2) le mnémotechnique reprend toute la liste, dans l'ordre, sans rien ajouter
        mp = m["mnemonic"]["mapping"]
        seq = [x["itemIndex"] for x in mp if x["itemIndex"] is not None]
        if any(k >= n for k in seq):
            r.error("E-MNEMO", where, f"itemIndex hors de la liste ({n} éléments)")
        elif ordered and seq != list(range(n)):
            r.error("E-MNEMO", where, f"éléments repris dans le mauvais ordre ou incomplets : {seq}")
        elif not ordered and sorted(seq) != list(range(n)):
            r.error("E-MNEMO", where, f"éléments manquants ou répétés : {sorted(seq)}")
        kind = m["mnemonic"]["kind"]
        if kind in ("acronym", "phrase"):
            for x in mp:
                k = x["itemIndex"]
                if k is not None and k < n and fold(x["token"])[:1] != fold(items[k])[:1]:
                    r.error("E-MNEMO", where, f"« {x['token']} » ne commence pas comme « {items[k]} »")
            sep = "" if kind == "acronym" else " "
            if normalize(sep.join(x["token"] for x in mp)) != normalize(m["mnemonic"]["text"]):
                r.error("E-MNEMO", where, "text diffère de l'assemblage des tokens (mot ajouté ou omis)")


# --------------------------------------------------------------------------- build : manifeste

def check_manifest(content: Path, report: Report) -> None:
    data = _load(content / "manifest.json", "manifest", "built", report)
    if data is None:
        return
    for f in data["files"]:
        p = content / f["path"]
        if not p.exists():
            report.error("E-MANIFEST", f["path"], "fichier listé absent")
        elif hashlib.sha256(p.read_bytes()).hexdigest() != f["sha256"]:
            report.error("E-MANIFEST", f["path"], "sha256 différent du manifeste")


# --------------------------------------------------------------------------- orchestration

def _load(path: Path, kind: str, stage: str, report: Report, required: bool = True):
    if not path.exists():
        if required:
            report.error("E-FILE", path.name, "fichier manquant")
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        report.error("E-JSON", path.name, f"JSON invalide : {e}")
        return None
    issues = schema_issues(kind, data, stage, path.name)
    report.issues.extend(issues)
    return None if issues else data


def validate_content(content: Path, work: Path, stage: str = "generated", cfg: Config | None = None) -> Report:
    """Valide un dossier de contenu (taxonomy, sources, bees, chapters/*) contre le texte extrait (work/pages)."""
    report = Report()
    ctx = Context(cfg=cfg or Config(), report=report, stage=stage, pages=PageIndex(work / "pages"), content=content)
    tax = _load(content / "taxonomy.json", "taxonomy", stage, report)
    srcs = _load(content / "sources.json", "sources", stage, report)
    bees = _load(content / "bees.json", "bees", stage, report)
    if tax is None or srcs is None or bees is None:
        return report
    for s in srcs["sources"]:
        _claim(ctx, s["id"], f"sources#{s['id']}")
        ctx.sources[s["id"]] = s
    for b in bees["bees"]:
        _claim(ctx, b["id"], f"bees#{b['id']}")
        ctx.bees[b["id"]] = b
    check_taxonomy(tax, ctx)
    check_bees(ctx)

    chapters_dir = content / "chapters"
    if chapters_dir.exists():
        for d in sorted(p for p in chapters_dir.iterdir() if p.is_dir()):
            if d.name not in ctx.chapters:
                report.error("E-REF", f"chapters/{d.name}", "dossier absent de la taxonomie")
    n_questions: Counter = Counter()
    n_sheets = n_mnemonics = 0
    for cid in ctx.chapters:
        d = chapters_dir / cid
        qpack = _load(d / "questions.json", "questions", stage, report, required=False)
        if qpack is not None:
            check_questions(qpack, cid, ctx)
            for q in qpack["questions"]:
                n_questions["total"] += 1
                n_questions[f"type_{q['type']}"] += 1
                n_questions[f"niveau_{q['difficulty']}"] += 1
                n_questions["prioritaires (abeille)"] += int(q["priority"])
                n_questions["a_verifier"] += int(q["verify"]["needsReview"])
        elif not (d / "questions.json").exists():
            report.warn("W-COVER-EMPTY", cid, "chapitre sans questions")
        spack = _load(d / "sheet.json", "sheet", stage, report, required=False)
        if spack is not None:
            check_sheet(spack, cid, ctx)
            n_sheets += 1
        elif not (d / "sheet.json").exists():
            report.warn("W-NO-SHEET", cid, "chapitre sans fiche de synthèse")
        mpack = _load(d / "mnemonics.json", "mnemonics", stage, report, required=False)
        if mpack is not None:
            check_mnemonics(mpack, cid, ctx)
            n_mnemonics += len(mpack["mnemonics"])
    if stage == "built":
        check_manifest(content, report)

    pri =[n for _, n in ctx.notions.values() if n["priority"]]
    report.stats = {
        "chapitres": len(ctx.chapters),
        "notions": len(ctx.notions),
        "notions abeille": len(pri),
        "chapitres incontournables": sum(1 for c in ctx.chapters.values() if c["tier"] == "incontournable"),
        "abeilles rattachées": sum(1 for b in ctx.bees.values() if b["attachment"]["status"] in BEE_OK),
        "abeilles ambiguës": len(report.ambiguous_bees),
        "fiches": n_sheets,
        "mnémotechniques": n_mnemonics,
        **{f"questions : {k}": v for k, v in sorted(n_questions.items())},
    }
    return report


def stamp_content(content: Path, work: Path) -> list[str]:
    """Pose gen.sourceHash (empreinte du cours) sur chaque pack généré. À lancer après chaque génération.

    Le générateur n'a jamais à calculer ce hash lui-même. Les packs sans bloc `gen` sont signalés, pas modifiés.
    """
    pages = PageIndex(work / "pages")
    tax = json.loads((content / "taxonomy.json").read_text(encoding="utf-8"))
    messages: list[str] = []
    for y in tax["years"]:
        for ue in y["ues"]:
            for m in ue["modules"]:
                for c in m["chapters"]:
                    digest = chapter_source_hash(pages, c["sourceIds"])
                    if digest is None:
                        messages.append(f"{c['id']} : texte extrait manquant, ignoré")
                        continue
                    for name in ("questions.json", "sheet.json", "mnemonics.json"):
                        path = content / "chapters" / c["id"] / name
                        if not path.exists():
                            continue
                        data = json.loads(path.read_text(encoding="utf-8"))
                        if "gen" not in data:
                            messages.append(f"{c['id']}/{name} : bloc gen absent (model, date, promptVersion), ignoré")
                            continue
                        if data["gen"].get("sourceHash") != digest:
                            data["gen"]["sourceHash"] = digest
                            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                            messages.append(f"{c['id']}/{name} : sourceHash posé")
    return messages
