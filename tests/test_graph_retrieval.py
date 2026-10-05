from src.graph_retrieval import bfs_subgraph, subgraph_to_text, retrieve_seeds


class Graph:
    nodes = [{'id': str(i), 'labels': ['Person' if i == 0 else 'Case'],
              'props': {'name': 'Sam' if i == 0 else str(i), 'doc_id': 'news-1'}} for i in range(6)]
    edges = [{'id': str(i), 'source': str(i), 'target': str(i + 1),
              'predicate': 'INVOLVED_IN', 'props': {'source_doc_ids': ['news-1']}} for i in range(5)]
    edges += [{'id': 'cycle', 'source': '2', 'target': '0', 'predicate': 'INVOLVED_IN', 'props': {}}]

    def run(self, query, **params):
        if 'neighbors' in query:
            return [{'edge': e, 'node': next(n for n in self.nodes if n['id'] ==
                    (e['target'] if e['source'] == params['id'] else e['source']))}
                    for e in self.edges if params['id'] in (e['source'], e['target'])]
        return [n for n in self.nodes if n['id'] in params.get('ids', [])]


def test_bfs_cycles_depth_and_paths():
    result = bfs_subgraph(Graph(), ['0', '0'], max_hops=2, max_nodes=20)
    assert {n['id'] for n in result['nodes']} == {'0', '1', '2', '3'}
    assert result['paths']['3'] == ['0', '2', '3']
    assert len({e['id'] for e in result['edges']}) == len(result['edges'])
    assert all(len(path) - 1 <= 2 for path in result['paths'].values())


def test_bfs_budget_empty_and_invalid_seed():
    assert bfs_subgraph(Graph(), [])['nodes'] == []
    assert bfs_subgraph(Graph(), ['missing'])['nodes'] == []
    result = bfs_subgraph(Graph(), ['0'], max_nodes=2)
    assert len(result['nodes']) == 2
    assert result['truncated'] is True
    ids = {n['id'] for n in result['nodes']}
    assert all(e['source'] in ids and e['target'] in ids for e in result['edges'])


def test_serialization_provenance_and_budget():
    result = bfs_subgraph(Graph(), ['0'], max_hops=1)
    facts = subgraph_to_text(result, max_facts=3)
    assert 0 < len(facts) <= 3
    assert any('news-1' in fact for fact in facts)
    assert subgraph_to_text(result, max_facts=0) == []


def test_seeds_cosine_and_person_alias_priority():
    index = [{'node_id': 'clause', 'labels': ['Clause'], 'text': 'law', 'embedding': [10., 0.], 'props': {}},
             {'node_id': 'person', 'labels': ['Person'], 'text': 'Dương Minh Tuấn',
              'embedding': [0., 1.], 'props': {'name': 'Dương Minh Tuấn', 'aliases': ['Hoàng Nato']}}]
    assert retrieve_seeds('luật', index, lambda _: [1., 0.], top_k=1) == ['clause']
    assert retrieve_seeds('Hoàng Nato bị bắt vì gì?', index, lambda _: [1., 0.]) == ['person']

