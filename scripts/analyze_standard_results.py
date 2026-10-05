"""Recover exact usage and judge evidence from the unmodified standard runner's audit."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def totals(calls):
    return {'calls': len(calls),
            'input_tokens_known': sum(c.get('input_tokens') or 0 for c in calls),
            'output_tokens_known': sum(c.get('output_tokens') or 0 for c in calls),
            'priced_usd_subtotal': sum(c.get('usd') or 0 for c in calls),
            'api_seconds': sum(c['seconds'] for c in calls),
            'unpriced_calls': sum(c.get('usd') is None for c in calls),
            'missing_usage_calls': sum(c.get('input_tokens') is None for c in calls)}


def main():
    audit = json.loads((ROOT / 'report/checkpoints/bench_kg_benchmark_audit_0.json').read_text(encoding='utf-8'))
    questions = json.loads((ROOT / 'data/benchmark_kg.json').read_text(encoding='utf-8'))
    calls = audit['calls']
    cursor = 0
    while cursor < len(calls) and calls[cursor]['kind'] == 'embedding':
        cursor += 1
    flat_index = calls[:cursor]
    start = cursor
    while cursor < len(calls) and calls[cursor]['kind'] == 'chat' and calls[cursor]['prompt'].startswith('Bạn trích xuất knowledge graph'):
        cursor += 1
    kg_build = calls[start:cursor]
    assert len(flat_index) == 176 and len(kg_build) == 20, 'Not a complete cold standard benchmark'
    rows = []
    for q in questions:
        for pipeline in ('flat', 'graph'):
            embedding, answer, judge = calls[cursor:cursor+3]
            assert embedding['kind'] == 'embedding' and embedding['text'] == q['question']
            assert answer['kind'] == judge['kind'] == 'chat'
            assert q['question'] in answer['prompt'] and q['question'] in judge['prompt']
            verdict = json.loads(re.sub(r'^```(?:json)?\s*|\s*```$', '', judge['answer'].strip()))
            rows.append({'id': q['id'], 'pipeline': pipeline, 'question': q['question'],
                         'answer': answer['answer'], 'usage': totals([embedding, answer]),
                         'judge': verdict, 'judge_usage': totals([judge]),
                         'prompt': answer['prompt'],
                         'has_255_highest_clause': 'phạt tù 20 năm hoặc tù chung thân' in answer['prompt'],
                         'has_mdma_100g_clause': 'khối lượng 100 gam trở lên' in answer['prompt']})
            cursor += 3
    assert cursor == len(calls), 'Unexpected additional calls'
    report = {'chat_model': audit['chat_model'], 'embedding_model': audit['embedding_model'],
              'flat_index_api_usage': totals(flat_index), 'kg_build_api_usage': totals(kg_build),
              'all_judge_usage': totals([c for c in calls if c['kind'] == 'chat' and c['prompt'].startswith('Chấm câu trả lời')]),
              'rows': rows,
              'note': 'API seconds exclude launcher pacing/Neo4j/serialization; wall times are in the grader TXT. USD excludes unknown embedding charges.'}
    # Judge detection by structural grouping also handles wording changes in the original prompt.
    report['all_judge_usage'] = {key: sum(r['judge_usage'][key] for r in rows)
                                 for key in rows[0]['judge_usage']}
    output = ROOT / 'report/benchmark_kg_standard.json'
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k not in ('rows',)}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
