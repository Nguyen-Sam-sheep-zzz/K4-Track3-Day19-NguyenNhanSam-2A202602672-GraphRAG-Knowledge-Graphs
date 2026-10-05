"""Separate node-vector + BFS retrieval extension; the lab grader remains untouched."""
from __future__ import annotations
from collections import deque
import math
import unicodedata


def snapshot(graph):
    nodes = graph.run('MATCH (n) RETURN elementId(n) AS id, labels(n) AS labels, '
                      'properties(n) AS props ORDER BY id')
    for node in nodes:
        node['props'].pop('embedding', None)
    edges = graph.run('MATCH (a)-[r]->(b) RETURN elementId(r) AS id, elementId(a) AS source, '
                     'elementId(b) AS target, type(r) AS predicate, properties(r) AS props ORDER BY id')
    return {'nodes': nodes, 'edges': edges}


def sources(props):
    return sorted(set(props.get('source_doc_ids', []) + ([props['doc_id']] if props.get('doc_id') else [])))


def export_triples(graph):
    data = snapshot(graph)
    nodes = {n['id']: n for n in data['nodes']}
    return [{'subject_id': e['source'], 'subject': nodes[e['source']]['props'].get('name') or
             nodes[e['source']]['props'].get('id'), 'predicate': e['predicate'],
             'object_id': e['target'], 'object': nodes[e['target']]['props'].get('name') or
             nodes[e['target']]['props'].get('id'), 'properties': e['props'],
             'source_doc_ids': sources(e['props'])} for e in data['edges']]


def node_text(node):
    p = node['props']
    values = [p.get(k, '') for k in ('name', 'id', 'title', 'summary', 'text')]
    values += p.get('aliases', [])
    return f"{','.join(node['labels'])}: " + ' | '.join(str(v) for v in values if v)[:3500]


def build_node_index(graph, embedding_fn, embed_many=None, batch_size=16):
    nodes = snapshot(graph)['nodes']
    index = []
    for start in range(0, len(nodes), batch_size):
        batch = nodes[start:start + batch_size]
        texts = [node_text(n) for n in batch]
        vectors = embed_many(texts) if embed_many else [embedding_fn(t) for t in texts]
        if len(vectors) != len(batch):
            raise ValueError('Node embedding count mismatch')
        records = [{'node_id': n['id'], 'labels': n['labels'], 'props': n['props'], 'text': t,
                    'source_doc_ids': sources(n['props']), 'embedding': v}
                   for n, t, v in zip(batch, texts, vectors)]
        graph.run('UNWIND $records AS row MATCH (n) WHERE elementId(n) = row.node_id '
                  'SET n.embedding = row.embedding, n.embedding_model = $model, n.embedding_text = row.text',
                  records=records, model=getattr(embedding_fn, '__self__', None).embedding_model
                  if hasattr(getattr(embedding_fn, '__self__', None), 'embedding_model') else 'injected')
        index.extend(records)
    return index


def _normalize(text):
    return ' '.join(unicodedata.normalize('NFC', text).lower().split())


def cosine(a, b):
    if len(a) != len(b):
        raise ValueError('Embedding dimension mismatch')
    denominator = math.sqrt(sum(x*x for x in a) * sum(y*y for y in b))
    return sum(x*y for x, y in zip(a, b)) / denominator if denominator else 0.0


def retrieve_seeds(question, node_index, embedding_fn, top_k=3):
    if top_k <= 0 or not node_index:
        return []
    query = embedding_fn(question)
    normalized = _normalize(question)
    named_people = [n['node_id'] for n in node_index if 'Person' in n['labels'] and
                    any(len(a) >= 3 and _normalize(a) in normalized for a in
                        [n['props'].get('name', ''), *n['props'].get('aliases', [])])]
    # All explicitly named people are seeds for comparisons, not just a single name.
    if named_people:
        return list(dict.fromkeys(named_people))
    substances = [n['node_id'] for n in node_index if 'Substance' in n['labels'] and
                  len(n['props'].get('name', '')) >= 3 and _normalize(n['props']['name']) in normalized]
    if substances and any(s in normalized for s in ('những', 'các vụ', 'liệt kê', 'cùng')):
        return list(dict.fromkeys(substances))
    ranked = sorted(node_index, key=lambda n: cosine(query, n['embedding']), reverse=True)
    return [n['node_id'] for n in ranked[:top_k]]


def bfs_subgraph(graph, seed_ids, max_hops=4, max_nodes=180):
    if max_hops < 0 or max_nodes < 0:
        raise ValueError('BFS limits must be non-negative')
    if not seed_ids or not max_nodes:
        return {'nodes': [], 'edges': [], 'paths': {}, 'truncated': bool(seed_ids)}
    rows = graph.run('MATCH (n) WHERE elementId(n) IN $ids RETURN elementId(n) AS id, '
                     'labels(n) AS labels, properties(n) AS props ORDER BY id', ids=list(dict.fromkeys(seed_ids)))
    nodes = {n['id']: n for n in rows[:max_nodes]}
    paths = {i: [i] for i in nodes}
    queue = deque((i, 0) for i in nodes)
    edges = {}
    truncated = len(rows) > max_nodes
    while queue:
        current, depth = queue.popleft()
        if depth >= max_hops:
            continue
        neighbors = graph.run(
            '// neighbors: ontology-pruned undirected BFS; MENTIONS is excluded to avoid legal substance hubs\n'
            'MATCH (n)-[r]-(m) WHERE elementId(n) = $id AND type(r) <> "MENTIONS" '
            'RETURN {id: elementId(m), labels: labels(m), props: properties(m)} AS node, '
            '{id: elementId(r), source: elementId(startNode(r)), target: elementId(endNode(r)), '
            'predicate: type(r), props: properties(r)} AS edge '
            'ORDER BY CASE type(r) WHEN "INVOLVED_IN" THEN 0 WHEN "CHARGED_WITH" THEN 1 '
            'WHEN "DEFINES" THEN 2 WHEN "HAS_CLAUSE" THEN 3 ELSE 4 END, elementId(m)', id=current)
        for row in neighbors:
            neighbor, edge = row['node'], row['edge']
            ident = neighbor['id']
            if ident not in nodes:
                if len(nodes) >= max_nodes:
                    truncated = True
                    continue
                nodes[ident] = neighbor
                paths[ident] = paths[current] + [ident]
                queue.append((ident, depth + 1))
            edges[edge['id']] = edge
    for node in nodes.values():
        node['props'].pop('embedding', None)
        node['props'].pop('embedding_text', None)
    return {'nodes': list(nodes.values()), 'edges': list(edges.values()),
            'paths': paths, 'truncated': truncated}


def subgraph_to_text(subgraph, max_facts=60):
    if max_facts <= 0:
        return []
    nodes = {n['id']: n for n in subgraph['nodes']}
    facts = []
    for edge in subgraph['edges']:
        a, b = nodes[edge['source']], nodes[edge['target']]
        pa, pb = a['props'], b['props']
        name_a, name_b = pa.get('name') or pa.get('id'), pb.get('name') or pb.get('id')
        attrs = '; '.join(f'{k}={v}' for k, v in edge['props'].items() if v and k != 'source_doc_ids')
        source = sources(edge['props'])
        facts.append(f"[{', '.join(source)}] {a['labels'][0]} {name_a} --{edge['predicate']} "
                     f"({attrs})--> {b['labels'][0]} {name_b}")
    for node in subgraph['nodes']:
        p = node['props']
        if 'Clause' in node['labels']:
            facts.append(f"[{', '.join(sources(p))}] {p.get('id')}: {p.get('text', '')}")
        elif 'Case' in node['labels']:
            facts.append(f"[{', '.join(sources(p))}] {p.get('name')}: {p.get('summary', '')}")
    # Legal text and case summaries must survive a high-degree graph's edge budget.
    important = [f for f in facts if '--' not in f or any(r in f for r in ('--INVOLVED_IN', '--CHARGED_WITH', '--DEFINES'))]
    remaining = [f for f in facts if f not in important]
    return list(dict.fromkeys(important + remaining))[:max_facts]
