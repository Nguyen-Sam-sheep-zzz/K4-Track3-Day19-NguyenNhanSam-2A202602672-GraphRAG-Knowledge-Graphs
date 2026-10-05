"""Context formatting/budget tests; Cypher is verified separately on real Neo4j."""

from src.graph import Neo4jGraph, prioritize_context_facts


def test_context_zero_budget_does_not_query_database():
    graph = Neo4jGraph.__new__(Neo4jGraph)

    def unexpected(*args, **kwargs):
        raise AssertionError("Zero budget should not read the database")

    graph.run = unexpected
    assert graph.context("Câu hỏi", [], max_facts=0) == []


def test_context_no_matching_sources_returns_no_invented_facts():
    graph = Neo4jGraph.__new__(Neo4jGraph)
    graph.seed_facts = lambda *args, **kwargs: ([], [])
    graph.run = lambda *args, **kwargs: []
    assert graph.context("Câu hỏi không có dữ liệu", []) == []


def test_context_prioritizes_maximum_penalty_for_toi_da_question():
    facts = [
        "[law] Điều 255 - khoản 1: bị phạt tù từ 02 năm đến 07 năm",
        "[law] Điều 255 - khoản 4: bị phạt tù 20 năm hoặc tù chung thân",
        "[news] Hoàng Nato bị bắt để điều tra",
    ]
    selected = prioritize_context_facts("Hoàng Nato bị bắt, mức phạt tù tối đa là bao nhiêu?", facts, 2)
    assert any("khoản 4" in fact for fact in selected)
