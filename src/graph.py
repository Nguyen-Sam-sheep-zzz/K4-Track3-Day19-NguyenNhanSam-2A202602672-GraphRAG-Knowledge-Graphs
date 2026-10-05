"""Knowledge Graph (Neo4j) + GraphRAG over two drug-topic knowledge bases.

Contract (fixed — bench_kg.py and the tests rely on it):
    link_entity(name, known)                       -> one of `known` or None          (KG-1)
    build_graph(graph, law_docs, news_docs, llm_fn)   load both KBs into Neo4j          (KG-2)
        every node created from ONE document carries the property `doc_id`
    Neo4jGraph.context(question, doc_ids)         -> list[str] facts                   (KG-3)
    GraphRAGAgent.answer(question, top_k)         -> str                               (KG-4)

Everything else in this file is a HINT: one possible ontology (below). Use it as is, change it,
or design your own — your own ontology + report/ONTOLOGY.md earns the bonus (see SUBMISSION.md).

Suggested ontology (Crime is the bridge between the law KB and the news KB):

    (:Article {id, title, law, doc_id})-[:DEFINES]->(:Crime {name})
    (:Article)-[:HAS_CLAUSE]->(:Clause {id, number, penalty, text})-[:MENTIONS]->(:Substance {name})
    (:Case {name, summary, date, doc_id})-[:CHARGED_WITH]->(:Crime)
    (:Case)-[:INVOLVES {amount}]->(:Substance)
    (:Case)-[:LOCATED_IN]->(:Location {name})
    (:Person {name, aliases})-[:INVOLVED_IN {role, sentence, charge}]->(:Case)
"""

from __future__ import annotations

import difflib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Callable

from .models import Document
from .store import EmbeddingStore

# Canonical substance names: the ones BLHS Chương XX lists, plus common ones in Vietnamese news.
SUBSTANCES = ["Heroine", "Cocaine", "Methamphetamine", "Amphetamine", "MDMA", "XLR-11", "Ketamine",
              "cần sa", "thuốc phiện", "côca"]
CLAUSE_START = re.compile(r"^(\d+)\.\s", re.MULTILINE)
FOOTNOTE = re.compile(r"\[\d+\]")

def load_markdown_docs(folder: str | Path) -> list[Document]:
    """Read crawler output (.md with a flat `key: "value"` front matter) into Documents."""
    docs = []
    for path in sorted(Path(folder).glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        _, front, body = raw.split("---", 2)
        metadata = {k: json.loads(v) for k, v in re.findall(r'^(\w+): (".*")$', front, re.MULTILINE)}
        docs.append(Document(id=metadata.get("doc_id", path.stem), content=body.strip(), metadata=metadata))
    return docs

def normalize_crime(name: str) -> str:
    """'Tội Mua bán trái phép chất ma túy' -> 'mua bán trái phép chất ma túy'."""
    name = re.sub(r"\s+", " ", unicodedata.normalize('NFC', name).strip().strip("\"'“”").lower())
    return name.removeprefix("tội ").strip()

def link_entity(name: str, known: list[str], normalize: Callable[[str], str] = normalize_crime) -> str | None:
    """Map a free-text mention (e.g. a charge written by a journalist) onto one canonical name in `known`."""
    if not name or not known:
        return None
    normalized_name = normalize(name)
    if not normalized_name:
        return None
    candidates = [(normalize(item), item) for item in known if item and normalize(item)]
    for normalized, original in candidates:
        if normalized == normalized_name:
            return original
    matches = difflib.get_close_matches(
        normalized_name, [normalized for normalized, _ in candidates], n=1, cutoff=0.8
    )
    if not matches:
        return None
    matched = matches[0]
    return next(original for normalized, original in candidates if normalized == matched)

def find_substances(text: str) -> list[str]:
    lowered = text.lower()
    return [name for name in SUBSTANCES if name.lower() in lowered]


def prioritize_context_facts(question: str, facts: list[str], max_facts: int) -> list[str]:
    """Keep facts that answer the requested legal level before generic seed edges."""
    if max_facts <= 0:
        return []
    q = unicodedata.normalize('NFC', question).lower()
    explicit_articles = re.findall(r"[đd]iều\s+\d+", q)
    asks_max = any(term in q for term in ('tối đa', 'cao nhất', 'mức cao nhất', 'chung thân', 'tử hình'))
    asks_basic = any(term in q for term in ('cơ bản', 'khung cơ bản', 'khoản 1'))

    def score(fact: str) -> tuple[int, int]:
        text = fact.lower()
        value = 0
        if explicit_articles and any(article in text for article in explicit_articles):
            value += 50
        if asks_max:
            if 'chung thân' in text or 'tử hình' in text:
                value += 40
            if 'khoản 4' in text or 'khoản 5' in text:
                value += 30
            if 'tối đa' in text or '20 năm' in text:
                value += 20
        if asks_basic and ('khoản 1' in text or '02 năm đến 07 năm' in text):
            value += 40
        if 'vụ việc' in text or 'mức án' in text or 'vai trò' in text:
            value += 15
        return value, -len(fact)

    unique = list(dict.fromkeys(facts))
    ranked = sorted(enumerate(unique), key=lambda item: (score(item[1]), -item[0]), reverse=True)
    return [fact for _, fact in ranked[:max_facts]]

# ----------------------------------------------------------------------------------------------
# HINT — suggested ontology: extraction helpers
# ----------------------------------------------------------------------------------------------

def parse_law_article(doc: Document) -> dict[str, Any]:
    """Deterministic (regex) extraction for one 'Điều' — law text is regular enough to skip the LLM."""
    article_id = doc.metadata["article"]                       # "Điều 251 BLHS"
    title = doc.metadata["title"].split(". ", 1)[-1]           # "Tội mua bán trái phép chất ma túy"
    body = FOOTNOTE.sub("", doc.content)
    starts = list(CLAUSE_START.finditer(body))
    clauses = []
    for index, start in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(body)
        text = body[start.start():end].strip()
        first_line = text.splitlines()[0]
        penalty = re.search(r"\bbị ((?:phạt|tù|cảnh cáo).+?)(?::|$)", first_line)
        clauses.append({
            "id": f"{article_id} khoản {start.group(1)}",
            "number": int(start.group(1)),
            "penalty": penalty.group(1).rstrip(".") if penalty else "",
            "text": text,
            "substances": find_substances(text),
        })
    return {
        "id": article_id,
        "law": doc.metadata.get("law", ""),
        "title": title,
        "doc_id": doc.id,
        "crime": normalize_crime(title) if title.startswith("Tội ") else None,
        "clauses": clauses,
    }

NEWS_EXTRACTION_PROMPT = """Bạn trích xuất knowledge graph từ một bài báo tiếng Việt về ma túy.
Chỉ dùng thông tin có trong bài. Trả về JSON đúng dạng:
{{"cases": [{{
  "name": "tên ngắn của vụ việc, ví dụ: Vụ mua bán 36kg ma túy tại TP.HCM",
  "summary": "1-2 câu tóm tắt",
  "date": "ngày xảy ra/xét xử nếu có, dạng YYYY-MM-DD hoặc chuỗi rỗng",
  "location": "tỉnh/thành phố, chuỗi rỗng nếu không rõ",
  "charges": ["tội danh, BẮT BUỘC chọn đúng nguyên văn từ DANH SÁCH TỘI DANH"],
  "substances": [{{"name": "tên chất, dùng tên chuẩn trong DANH SÁCH CHẤT nếu khớp", "amount": "khối lượng nếu có"}}],
  "people": [{{"name": "họ tên", "aliases": ["biệt danh"], "role": "bị cáo|bị can|nghi phạm|người liên quan|cán bộ",
               "charge": "tội danh của người này (từ DANH SÁCH TỘI DANH) hoặc chuỗi rỗng",
               "sentence": "mức án nếu có, ví dụ: tử hình, 8 năm tù"}}]
}}]}}
Bài không nói về vụ việc cụ thể (tuyên truyền, hội nghị...) thì trả về {{"cases": []}}.

DANH SÁCH TỘI DANH: {crimes}
DANH SÁCH CHẤT: {substances}

Tiêu đề: {title}
Nội dung:
{content}"""

def extract_news_cases(doc: Document, llm_fn: Callable[[str], str], known_crimes: list[str]) -> list[dict]:
    """LLM extraction for one news article; charges are re-linked to law-KB crimes in code."""
    prompt = NEWS_EXTRACTION_PROMPT.format(
        crimes="; ".join(known_crimes), substances=", ".join(SUBSTANCES),
        title=doc.metadata.get("title", ""), content=doc.content[:12000],
    )
    try:
        payload = json.loads(llm_fn(prompt))
        if not isinstance(payload, dict) or not isinstance(payload.get('cases'), list):
            raise ValueError('cases must be a list')
        cases = payload['cases']
        for case in cases:
            if not isinstance(case, dict):
                raise ValueError('case must be an object')
            for field in ('charges', 'people', 'substances'):
                if not isinstance(case.get(field, []), list):
                    raise ValueError(f'{field} must be a list')
            if any(not isinstance(p, dict) for p in case.get('people', []) + case.get('substances', [])):
                raise ValueError('people/substances must contain objects')
            if any(not isinstance(c, str) for c in case.get('charges', [])):
                raise ValueError('charges must contain strings')
    except (json.JSONDecodeError, ValueError) as error:
        raise ValueError(f'Extraction failed for {doc.id}: {error}') from error
    for case in cases:
        case["charges"] = sorted({c for c in (link_entity(x, known_crimes) for x in case.get("charges", [])) if c})
        for person in case.get("people", []):
            for field in ('name', 'role', 'sentence'):
                person[field] = unicodedata.normalize('NFC', str(person.get(field) or '')).strip()
            person['aliases'] = [str(a).strip() for a in (person.get('aliases') or []) if a]
            person["charge"] = link_entity(person.get("charge") or "", known_crimes) or ""
        for substance in case.get('substances', []):
            substance['name'] = link_entity(str(substance.get('name') or ''), SUBSTANCES,
                                            normalize=lambda s: s.strip().lower()) or str(substance.get('name') or '').strip()
            substance['amount'] = str(substance.get('amount') or '')
    return cases

# ----------------------------------------------------------------------------------------------
# Neo4j
# ----------------------------------------------------------------------------------------------

class Neo4jGraph:
    """Thin wrapper over the official neo4j driver."""

    def __init__(self, uri: str, user: str, password: str) -> None:
        from neo4j import GraphDatabase

        self.driver = GraphDatabase.driver(uri, auth=(user, password), notifications_min_severity="OFF")
        self.driver.verify_connectivity()

    def close(self) -> None:
        self.driver.close()

    def run(self, cypher: str, **params: Any) -> list[dict]:
        records, _, _ = self.driver.execute_query(cypher, params)
        return [record.data() for record in records]

    def reset(self) -> None:
        """Delete every node, relationship and constraint (bench_kg.py calls this before build_graph)."""
        self.run("MATCH (n) DETACH DELETE n")
        for row in self.run("SHOW CONSTRAINTS YIELD name RETURN name"):
            self.run(f"DROP CONSTRAINT `{row['name']}` IF EXISTS")

    def stats(self) -> dict[str, int]:
        nodes = self.run("MATCH (n) RETURN count(n) AS n")[0]["n"]
        rels = self.run("MATCH ()-[r]->() RETURN count(r) AS n")[0]["n"]
        return {"nodes": nodes, "relationships": rels}

    def seed_facts(self, question: str, doc_ids: list[str], skip_labels: tuple[str, ...] = (),
                   limit: int = 60) -> tuple[list[str], list[str]]:
        """Ontology-independent first step: seed nodes + their 1-hop edges as text facts.

        Seeds = nodes whose `doc_id` is in doc_ids, or whose `name`/`aliases` appear in the question.
        Returns (seed elementIds, facts). Nodes with a label in skip_labels are left out of the facts.
        """
        seeds = self.run(
            """
            MATCH (n)
            WHERE n.doc_id IN $doc_ids
               OR any(d IN coalesce(n.source_doc_ids, []) WHERE d IN $doc_ids)
               OR (n.name IS :: STRING AND size(n.name) >= 3 AND toLower($q) CONTAINS toLower(n.name))
               OR any(a IN coalesce(n.aliases, []) WHERE size(a) >= 3 AND toLower($q) CONTAINS toLower(a))
            RETURN elementId(n) AS id
            """,
            q=question, doc_ids=doc_ids,
        )
        seed_ids = [row["id"] for row in seeds]
        edges = self.run(
            """
            MATCH (s)-[r]-(m)
            WHERE elementId(s) IN $ids
              AND none(l IN labels(s) + labels(m) WHERE l IN $skip)
            WITH DISTINCT r LIMIT $limit
            WITH startNode(r) AS a, r, endNode(r) AS b
            RETURN labels(a)[0] AS a_label, coalesce(a.name, a.id) AS a_name, type(r) AS rel,
                   properties(r) AS props, labels(b)[0] AS b_label, coalesce(b.name, b.id) AS b_name
            """,
            ids=seed_ids, skip=list(skip_labels), limit=limit,
        )
        facts = []
        for e in edges:
            props = ", ".join(f"{k}: {v}" for k, v in e["props"].items() if v)
            facts.append(f"({e['a_label']}: {e['a_name']}) -[{e['rel']}{' {' + props + '}' if props else ''}]-> "
                         f"({e['b_label']}: {e['b_name']})")
        return seed_ids, facts

    # ---------------------------------------------------------------- HINT — suggested ontology: writes

    def suggested_constraints(self) -> None:
        for label, key in [("Article", "id"), ("Clause", "id"), ("Crime", "name"), ("Case", "name"),
                           ("Substance", "name"), ("Person", "name"), ("Location", "name")]:
            self.run(f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.{key} IS UNIQUE")

    def add_law_article(self, article: dict) -> None:
        self.run(
            """
            MERGE (a:Article {id: $id}) SET a.title = $title, a.law = $law, a.doc_id = $doc_id
            FOREACH (crime IN CASE WHEN $crime IS NULL THEN [] ELSE [$crime] END |
                MERGE (c:Crime {name: crime})
                SET c.source_doc_ids = CASE WHEN c.source_doc_ids IS NULL THEN [$doc_id]
                                            WHEN $doc_id IN c.source_doc_ids THEN c.source_doc_ids
                                            ELSE c.source_doc_ids + $doc_id END
                MERGE (a)-[r:DEFINES]->(c) SET r.source_doc_ids = [$doc_id])
            WITH a
            UNWIND $clauses AS clause
            MERGE (cl:Clause {id: clause.id})
              SET cl.number = clause.number, cl.penalty = clause.penalty, cl.text = clause.text, cl.doc_id = $doc_id
            MERGE (a)-[hc:HAS_CLAUSE]->(cl) SET hc.source_doc_ids = [$doc_id]
            FOREACH (s IN clause.substances |
                MERGE (sub:Substance {name: s})
                SET sub.source_doc_ids = CASE WHEN sub.source_doc_ids IS NULL THEN [$doc_id]
                                              WHEN $doc_id IN sub.source_doc_ids THEN sub.source_doc_ids
                                              ELSE sub.source_doc_ids + $doc_id END
                MERGE (cl)-[m:MENTIONS]->(sub) SET m.source_doc_ids = [$doc_id])
            """,
            **article,
        )

    def add_news_case(self, case: dict, doc: Document) -> None:
        self.run(
            """
            MERGE (k:Case {name: $name})
              SET k.summary = $summary, k.date = $date, k.doc_id = coalesce(k.doc_id, $doc_id), k.source_title = $title,
                  k.source_doc_ids = CASE WHEN k.source_doc_ids IS NULL THEN [$doc_id]
                                         WHEN $doc_id IN k.source_doc_ids THEN k.source_doc_ids
                                         ELSE k.source_doc_ids + $doc_id END
            FOREACH (loc IN CASE WHEN $location = '' THEN [] ELSE [$location] END |
                MERGE (l:Location {name: loc})
                SET l.doc_id = coalesce(l.doc_id, $doc_id),
                    l.source_doc_ids = CASE WHEN l.source_doc_ids IS NULL THEN [$doc_id]
                                            WHEN $doc_id IN l.source_doc_ids THEN l.source_doc_ids
                                            ELSE l.source_doc_ids + $doc_id END
                MERGE (k)-[r:LOCATED_IN]->(l)
                SET r.source_doc_ids = CASE WHEN r.source_doc_ids IS NULL THEN [$doc_id]
                                            WHEN $doc_id IN r.source_doc_ids THEN r.source_doc_ids
                                            ELSE r.source_doc_ids + $doc_id END)
            FOREACH (crime IN $charges |
                MERGE (c:Crime {name: crime})
                SET c.source_doc_ids = CASE WHEN c.source_doc_ids IS NULL THEN [$doc_id]
                                            WHEN $doc_id IN c.source_doc_ids THEN c.source_doc_ids
                                            ELSE c.source_doc_ids + $doc_id END
                MERGE (k)-[r:CHARGED_WITH]->(c)
                SET r.source_doc_ids = CASE WHEN r.source_doc_ids IS NULL THEN [$doc_id]
                                            WHEN $doc_id IN r.source_doc_ids THEN r.source_doc_ids
                                            ELSE r.source_doc_ids + $doc_id END)
            FOREACH (s IN $substances |
                MERGE (sub:Substance {name: s.name})
                SET sub.source_doc_ids = CASE WHEN sub.source_doc_ids IS NULL THEN [$doc_id]
                                              WHEN $doc_id IN sub.source_doc_ids THEN sub.source_doc_ids
                                              ELSE sub.source_doc_ids + $doc_id END
                MERGE (k)-[r:INVOLVES]->(sub)
                SET r.amount = s.amount,
                    r.source_doc_ids = CASE WHEN r.source_doc_ids IS NULL THEN [$doc_id]
                                            WHEN $doc_id IN r.source_doc_ids THEN r.source_doc_ids
                                            ELSE r.source_doc_ids + $doc_id END)
            FOREACH (p IN $people | MERGE (person:Person {name: p.name})
                SET person.aliases = reduce(acc = coalesce(person.aliases, []), alias IN coalesce(p.aliases, []) |
                                            CASE WHEN alias IN acc THEN acc ELSE acc + alias END),
                    person.doc_id = coalesce(person.doc_id, $doc_id),
                    person.source_doc_ids = CASE WHEN person.source_doc_ids IS NULL THEN [$doc_id]
                                                 WHEN $doc_id IN person.source_doc_ids THEN person.source_doc_ids
                                                 ELSE person.source_doc_ids + $doc_id END
                MERGE (person)-[r:INVOLVED_IN]->(k) SET r.role = p.role, r.charge = p.charge, r.sentence = p.sentence,
                    r.source_doc_ids = CASE WHEN r.source_doc_ids IS NULL THEN [$doc_id]
                                            WHEN $doc_id IN r.source_doc_ids THEN r.source_doc_ids
                                            ELSE r.source_doc_ids + $doc_id END)
            """,
            name=case.get("name") or doc.metadata.get("title", doc.id),
            summary=case.get("summary", ""), date=case.get("date", ""), location=case.get("location", ""),
            charges=case.get("charges", []), people=[p for p in case.get("people", []) if p.get("name")],
            substances=[s for s in case.get("substances", []) if s.get("name")],
            doc_id=doc.id, title=doc.metadata.get("title", ""),
        )

    # ---------------------------------------------------------------- KG-3

    def context(self, question: str, doc_ids: list[str], max_facts: int = 60) -> list[str]:
        """Graph facts for a question: seeds + 1 hop, then the legal basis of every case reached."""
        if max_facts <= 0:
            return []
        seed_ids, seed_facts = self.seed_facts(question, doc_ids, limit=max_facts)
        substances = find_substances(question)
        aggregation = any(term in question.lower() for term in ("những vụ", "các vụ", "liệt kê", "tất cả"))
        people = self.run(
            """
            MATCH (p:Person)
            WHERE toLower($q) CONTAINS toLower(p.name)
               OR any(a IN coalesce(p.aliases, []) WHERE size(a) >= 3 AND toLower($q) CONTAINS toLower(a))
            RETURN elementId(p) AS id
            """, q=question,
        )
        person_ids = [row["id"] for row in people]
        cases = self.run(
            """
            MATCH (k:Case)
            WHERE ($aggregate AND EXISTS {
                       MATCH (k)-[:INVOLVES]->(s:Substance) WHERE s.name IN $substances
                   })
               OR (NOT $aggregate AND size($people) > 0 AND EXISTS {
                       MATCH (p:Person)-[:INVOLVED_IN]->(k) WHERE elementId(p) IN $people
                   })
               OR (NOT $aggregate AND size($people) = 0 AND
                   (k.doc_id IN $docs OR elementId(k) IN $seeds))
            RETURN elementId(k) AS id, k.name AS name, k.summary AS summary, k.doc_id AS doc_id
            ORDER BY k.doc_id, k.name
            """, aggregate=aggregation, substances=substances, people=person_ids,
            docs=doc_ids, seeds=seed_ids,
        )
        case_ids = [row["id"] for row in cases]
        facts = [f"[{row['doc_id']}] Vụ việc '{row['name']}': {row['summary']}" for row in cases]
        if case_ids:
            rows = self.run(
                """
                MATCH (p:Person)-[r:INVOLVED_IN]->(k:Case)
                WHERE elementId(k) IN $cases
                RETURN p.name AS name, r.role AS role, r.charge AS charge, r.sentence AS sentence,
                       k.name AS case_name, k.doc_id AS doc_id
                ORDER BY p.name
                """, cases=case_ids,
            )
            for row in rows:
                facts.append(f"[{row['doc_id']}] {row['name']} trong '{row['case_name']}': "
                             f"vai trò {row['role'] or 'không rõ'}; tội {row['charge'] or 'chưa rõ'}; "
                             f"mức án {row['sentence'] or 'nguồn không nêu'}")
            rows = self.run(
                """
                MATCH (k:Case)-[r:INVOLVES]->(s:Substance)
                WHERE elementId(k) IN $cases
                RETURN k.name AS case_name, k.doc_id AS doc_id, s.name AS name, r.amount AS amount
                ORDER BY k.name, s.name
                """, cases=case_ids,
            )
            facts.extend(f"[{row['doc_id']}] '{row['case_name']}' có {row['name']}: "
                         f"{row['amount'] or 'nguồn không nêu khối lượng'}" for row in rows)

        article_numbers = re.findall(r"[Đđ]iều\s+(\d+)", question)
        clauses = self.run(
            """
            MATCH (a:Article)-[:HAS_CLAUSE]->(cl:Clause)
            WHERE a.doc_id IN $docs
               OR any(number IN $numbers WHERE a.id STARTS WITH 'Điều ' + number + ' ')
               OR EXISTS {
                   MATCH (k:Case)-[:CHARGED_WITH]->(:Crime)<-[:DEFINES]-(a)
                   WHERE elementId(k) IN $cases
               }
            RETURN DISTINCT a.id AS article_id, a.title AS title, a.doc_id AS doc_id,
                   cl.number AS number, cl.text AS text
            ORDER BY article_id, number
            """, docs=doc_ids, numbers=article_numbers, cases=case_ids,
        )
        # Keep the full clauses: a substance-only filter loses maximum penalties and definitions.
        facts.extend(f"[{row['doc_id']}; {row['article_id']} - {row['title']}] "
                     f"khoản {row['number']}: {row['text']}" for row in clauses)
        return prioritize_context_facts(question, facts + seed_facts, max_facts)

# ---------------------------------------------------------------------------------------------- KG-2

def build_graph(graph: Neo4jGraph, law_docs: list[Document], news_docs: list[Document],
                llm_fn: Callable[..., str]) -> None:
    """Load both KBs into an empty graph. llm_fn(prompt, json_mode=False) -> str (metered OpenAI chat)."""
    graph.suggested_constraints()
    articles = [parse_law_article(doc) for doc in law_docs]
    for article in articles:
        graph.add_law_article(article)

    known_crimes = sorted({article["crime"] for article in articles if article.get("crime")})
    for doc in news_docs:
        cases = extract_news_cases(
            doc,
            lambda prompt: llm_fn(prompt, json_mode=True),
            known_crimes,
        )
        for case in cases:
            graph.add_news_case(case, doc)

# ---------------------------------------------------------------------------------------------- KG-4

GRAPH_PROMPT = """Trả lời câu hỏi chỉ dựa trên ngữ cảnh (đoạn văn bản và dữ kiện từ knowledge graph).
Nêu rõ số Điều luật khi có. Nếu ngữ cảnh không đủ, nói không đủ thông tin.

Dữ kiện knowledge graph:
{facts}

Đoạn văn bản:
{chunks}

Câu hỏi: {question}
Trả lời:"""

class GraphRAGAgent:
    """Hybrid GraphRAG: the same vector top-k as flat RAG, plus facts expanded from the graph."""

    def __init__(self, store: EmbeddingStore, graph: Neo4jGraph, llm_fn: Callable[[str], str]) -> None:
        self.store = store
        self.graph = graph
        self.llm_fn = llm_fn

    def answer(self, question: str, top_k: int = 3) -> str:
        chunks = self.store.search(question, top_k=top_k)
        doc_ids = list(dict.fromkeys(
            chunk.get("metadata", {}).get("doc_id")
            for chunk in chunks
            if chunk.get("metadata", {}).get("doc_id")
        ))
        facts = self.graph.context(question, doc_ids)
        chunk_text = "\n\n".join(
            f"[{index}] {chunk['content']}" for index, chunk in enumerate(chunks, start=1)
        )
        fact_text = "\n".join(f"- {fact}" for fact in facts) or "(Không có dữ kiện graph phù hợp.)"
        prompt = GRAPH_PROMPT.format(
            facts=fact_text,
            chunks=chunk_text,
            question=question,
        )
        return self.llm_fn(prompt)
