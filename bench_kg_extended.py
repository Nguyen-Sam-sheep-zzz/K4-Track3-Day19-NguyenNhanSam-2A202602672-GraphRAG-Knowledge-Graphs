"""20-question experiment on the final lab graph; never modifies the original grader.

Run after scripts/run_local.py bench_kg.py --judge:
    python scripts/run_local.py bench_kg_extended.py --judge
Reuses the paid chunk vectors and the graph from that run. Node indexing is measured separately.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import statistics
import time

from bench_kg import JUDGE_PROMPT, chunk_docs, connect_graph, keyword_recall, load_corpus, metered
from src.llm import MeteredLLM, Usage
from src.store import EmbeddingStore
from src.graph import GRAPH_PROMPT
from src.graph_retrieval import build_node_index, retrieve_seeds, bfs_subgraph, subgraph_to_text, export_triples, snapshot


def dump(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def criterion_recall(answer, criteria):
    lowered = answer.lower()
    return sum(any(option.lower() in lowered for option in group) for group in criteria) / len(criteria)


def summarize(rows, pipeline):
    mine = [r for r in rows if r['pipeline'] == pipeline]
    times = sorted(r['usage']['seconds'] for r in mine)
    return {'n': len(mine), 'keyword_recall': statistics.mean(r['recall'] for r in mine),
            'criterion_recall': statistics.mean(r['criterion_recall'] for r in mine),
            'accuracy_judge_full': statistics.mean(r.get('judge', {}).get('score') == 2 for r in mine)
                if all('judge' in r for r in mine) else None,
            'mean_judge': statistics.mean(r['judge']['score'] for r in mine) if all('judge' in r for r in mine) else None,
            'mean_seconds': statistics.mean(times), 'p95_seconds': times[max(0, int(len(times)*.95 + .999)-1)],
            'priced_usd_subtotal': sum(r['usage']['usd'] for r in mine),
            'unpriced_calls': sum(r['usage']['unpriced_calls'] for r in mine),
            'missing_usage_calls': sum(r['usage']['missing_usage_calls'] for r in mine)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--questions', default='data/benchmark_kg_20.json')
    parser.add_argument('--judge', action='store_true')
    parser.add_argument('--out', default='report/benchmark_kg_extended.json')
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    llm = MeteredLLM()
    law, news = load_corpus()
    chunks = chunk_docs(law + news, 800)
    cached = json.loads(Path('.cache/bench_kg_benchmark_embeddings.json').read_text(encoding='utf-8'))
    if cached['model'] != llm.embedding_model or any(c.content not in cached['vectors'] for c in chunks):
        raise ValueError('Chunk cache model/corpus differs; rerun the standard benchmark first')
    store = EmbeddingStore('extended', embedding_fn=llm.embed)
    for i, doc in enumerate(chunks, 1):
        store._store.append({'id': f'{doc.id}#{i}', 'content': doc.content,
                             'metadata': doc.metadata, 'embedding': cached['vectors'][doc.content]})
    graph = connect_graph()
    graph_data = snapshot(graph)
    fingerprint_data = [{'id': n['id'], 'labels': n['labels'], 'props': {k: v for k, v in n['props'].items()
                       if k not in ('embedding_model', 'embedding_text')}} for n in graph_data['nodes']]
    fingerprint = hashlib.sha256(json.dumps([fingerprint_data, graph_data['edges']],
                                ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    questions = json.loads(Path(args.questions).read_text(encoding='utf-8'))
    if len(questions) != 20 or len({q['id'] for q in questions}) != 20:
        raise ValueError('Expected 20 unique multi-hop questions')
    base_audit = json.loads(Path('report/checkpoints/bench_kg_benchmark_audit_0.json').read_text(encoding='utf-8'))
    baseline_index_calls = []
    for call in base_audit['calls']:
        if call['kind'] == 'chat' and not call['prompt'].startswith('Bạn trích xuất knowledge graph'):
            break
        baseline_index_calls.append(call)
    index_path = Path('.cache/node_index.json')
    if index_path.exists():
        saved = json.loads(index_path.read_text(encoding='utf-8'))
    else:
        saved = {}
    if saved.get('fingerprint') == fingerprint and saved.get('model') == llm.embedding_model:
        index, node_usage = saved['index'], saved['usage']
        print(f"Reuse node index: {len(index)} nodes; original node indexing usage preserved", flush=True)
    else:
        index, usage = metered(llm, lambda: build_node_index(graph, llm.embed, llm.embed_many))
        node_usage = asdict(usage)
        dump(index_path, {'fingerprint': fingerprint, 'model': llm.embedding_model,
                          'index': index, 'usage': node_usage})
        print(f"Node index: {len(index)} nodes, {usage.calls} batched requests, {usage.seconds:.2f}s", flush=True)
    dump('report/triples.json', export_triples(graph))
    # A compact public artifact proves nodes have vectors; the vectors themselves stay in .cache/Neo4j.
    dump('report/node_index_metadata.json', {'model': llm.embedding_model, 'fingerprint': fingerprint,
         'nodes': [{k: v for k, v in n.items() if k not in ('embedding', 'props')} |
                   {'dimensions': len(n['embedding'])} for n in index], 'usage': node_usage})
    config = {'chat_model': llm.chat_model, 'embedding_model': llm.embedding_model,
              'top_k': 3, 'chunk_size': 800, 'max_hops': 4, 'max_nodes': 180, 'max_facts': 100,
              'excluded_bfs_relationships': ['MENTIONS'], 'graph_fingerprint': fingerprint,
              'question_sha256': hashlib.sha256(Path(args.questions).read_bytes()).hexdigest(),
              'reuse_note': 'Both pipelines reuse standard chunk vectors; graph additionally reuses KG; node-index cost separate.'}
    result = {'config': config, 'stats': graph.stats(), 'chunks': len(chunks),
              'node_index_usage': node_usage, 'baseline_index_calls': baseline_index_calls, 'rows': [],
              'cost_note': 'USD is priced subtotal only; Gemini embedding token usage and price unknown. Not an invoice.',
              'evaluation_note': 'Accuracy = fraction scored 2 by the same LLM judge, not independently verified human accuracy.'}
    if args.resume and Path(args.out).exists():
        previous = json.loads(Path(args.out).read_text(encoding='utf-8'))
        if previous['config'] != config:
            raise ValueError('Resume config/graph/questions changed')
        result['rows'] = previous['rows']
    try:
        for q in questions:
            for pipeline in ('flat', 'graph_bfs'):
                if any(r['id'] == q['id'] and r['pipeline'] == pipeline for r in result['rows']):
                    continue
                trace = {}
                def answer():
                    chunks_found = store.search(q['question'], top_k=3)
                    trace['chunks'] = chunks_found
                    chunk_text = '\n\n'.join(f"[{i}] {c['content']}" for i, c in enumerate(chunks_found, 1))
                    if pipeline == 'flat':
                        prompt = ('Trả lời câu hỏi chỉ dựa trên ngữ cảnh. Nếu ngữ cảnh không đủ, nói không đủ thông tin.\n\n'
                                  f"Ngữ cảnh:\n{chunk_text}\n\nCâu hỏi: {q['question']}\nTrả lời:")
                    else:
                        seeds = retrieve_seeds(q['question'], index, llm.embed, top_k=3)
                        subgraph = bfs_subgraph(graph, seeds, max_hops=4, max_nodes=180)
                        facts = subgraph_to_text(subgraph, max_facts=100)
                        trace.update(seed_ids=seeds, subgraph=subgraph, facts=facts)
                        prompt = GRAPH_PROMPT.format(facts='\n'.join(facts), chunks=chunk_text, question=q['question'])
                    trace['prompt'] = prompt
                    return llm.chat(prompt)
                response, usage = metered(llm, answer)
                row = {'id': q['id'], 'type': q['type'], 'pipeline': pipeline,
                       'question': q['question'], 'gold': q['gold'], 'sources': q['sources'],
                       'answer': response, 'usage': asdict(usage), 'trace': trace,
                       'recall': keyword_recall(response, q['must_include']),
                       'criterion_recall': criterion_recall(response, q['criteria'])}
                if args.judge:
                    verdict, judge_usage = metered(llm, lambda: llm.chat(JUDGE_PROMPT.format(
                        question=q['question'], gold=q['gold'], answer=response), json_mode=True))
                    parsed = json.loads(verdict)
                    if parsed.get('score') not in (0, 1, 2):
                        raise ValueError(f'Invalid judge score for {q["id"]}')
                    row.update(judge=parsed, judge_usage=asdict(judge_usage))
                result['rows'].append(row)
                dump(args.out, result)
                print(f"{q['id']} {pipeline:9} recall={row['recall']:.2f} "
                      f"judge={row.get('judge', {}).get('score', '-')} {usage.seconds:.2f}s", flush=True)
        result['summary'] = {p: summarize(result['rows'], p) for p in ('flat', 'graph_bfs')}
        dump(args.out, result)
        print(json.dumps(result['summary'], ensure_ascii=False, indent=2), flush=True)
    finally:
        graph.close()


if __name__ == '__main__':
    main()
