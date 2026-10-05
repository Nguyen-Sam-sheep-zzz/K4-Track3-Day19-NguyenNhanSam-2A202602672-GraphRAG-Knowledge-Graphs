"""Read-only local delivery audit. Secret findings report filenames, never values."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    result = subprocess.run(['git', '-c', f'safe.directory={ROOT.as_posix()}', *args],
                            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return result.stdout


def digest(data):
    return hashlib.sha256(data.replace(b'\r\n', b'\n')).hexdigest()


def main():
    frozen = ['bench_kg.py', 'tests/test_base.py', 'tests/test_graph.py', 'data/benchmark_kg.json']
    original = {p: digest((ROOT / p).read_bytes()) == digest(git('show', f'859e8d1:{p}')) for p in frozen}
    local_keys = []
    for line in (ROOT / '.env').read_text(encoding='utf-8-sig').splitlines():
        match = re.match(r'\s*(?:OPENAI|OPENROUTER|GEMINI|ANTHROPIC)_API_KEY\s*=\s*(.+)', line)
        if match:
            key = match.group(1).strip().strip('"\'')
            if len(key) >= 8:
                local_keys.append(key.encode())
    candidates = git('ls-files', '--cached', '--others', '--exclude-standard', '-z').decode().split('\0')
    leak_paths = []
    key_patterns = [rb'sk-[A-Za-z0-9_-]{20,}', rb'AIza[0-9A-Za-z_-]{25,}']
    for relative in filter(None, candidates):
        file = ROOT / relative
        if not file.is_file() or file.suffix.lower() in ('.png', '.jpg', '.zip', '.pdf'):
            continue
        data = file.read_bytes()
        if any(key in data for key in local_keys) or any(re.search(pattern, data) for pattern in key_patterns):
            leak_paths.append(relative)
    history = git('log', '--all', '-p', '--format=%H')
    history_clean = not (any(key in history for key in local_keys) or any(re.search(p, history) for p in key_patterns))
    tracked = git('ls-files', '-z').decode().split('\0')
    secrets_untracked = not any(p == '.env' or p.startswith(('.venv/', '.cache/')) for p in tracked)
    standard = json.loads((ROOT / 'report/benchmark_kg_standard.json').read_text(encoding='utf-8'))
    extended = json.loads((ROOT / 'report/benchmark_kg_extended.json').read_text(encoding='utf-8'))
    evidence = json.loads((ROOT / 'report/graph_evidence.json').read_text(encoding='utf-8'))
    metadata = json.loads((ROOT / 'report/node_index_metadata.json').read_text(encoding='utf-8'))
    triples = json.loads((ROOT / 'report/triples.json').read_text(encoding='utf-8'))
    qs = json.loads((ROOT / 'data/benchmark_kg_20.json').read_text(encoding='utf-8'))
    source_ids = {p.stem for folder in ('drug_news', 'drug_law') for p in (ROOT / 'data' / folder).glob('*.md')}
    rows = extended['rows']
    bfs = [r['trace']['subgraph'] for r in rows if r['pipeline'] == 'graph_bfs']
    expected = {(q['id'], p) for q in qs for p in ('flat', 'graph_bfs')}
    checks = {
        'frozen_original_files': original,
        'api_secret_leak_paths': leak_paths,
        'git_history_api_secret_clean': history_clean,
        'env_venv_cache_not_tracked': secrets_untracked,
        'standard_12_rows': len(standard['rows']) == 12,
        'extended_40_unique_rows': len(rows) == 40 and {(r['id'], r['pipeline']) for r in rows} == expected,
        'extended_summary_present': 'summary' in extended,
        'all_20_question_sources_exist': all(s in source_ids for q in qs for s in q['sources']),
        'graph_stats_match_standard_extended': evidence['stats'] == extended['stats'],
        'triples_count_matches_relationships': len(triples) == evidence['stats']['relationships'],
        'all_triples_have_sources': all(t['source_doc_ids'] for t in triples),
        'all_nodes_have_3072d_metadata': len(metadata['nodes']) == evidence['stats']['nodes'] and
                                      all(n['dimensions'] == 3072 for n in metadata['nodes']),
        'neo4j_all_nodes_have_embeddings': evidence['embedding_counts']['rows'][0]['embedded_nodes'] == evidence['stats']['nodes'],
        'bfs_limits_and_unique_nodes': all(len(s['nodes']) <= 180 and len({n['id'] for n in s['nodes']}) == len(s['nodes'])
                                         and all(len(p) <= 5 for p in s['paths'].values()) for s in bfs),
        'judge_scores_valid': all(r.get('judge', {}).get('score') in (0, 1, 2) for r in rows),
        'three_pngs_present': all((ROOT / 'report/img' / name).read_bytes().startswith(b'\x89PNG')
                                 for name in ('kg_count.png', 'kg_cross_kb.png', 'kg_my_case.png')),
        'reports_present_no_template': all((ROOT / 'report' / name).is_file() and
                                          '(dán vào đây)' not in (ROOT / 'report' / name).read_text(encoding='utf-8')
                                          for name in ('ONTOLOGY.md', 'REPORT_KG.md', 'REPORT_KG_EXTENDED.md')),
    }
    passed = all(original.values()) and not leak_paths and all(v for k, v in checks.items()
                                                              if k not in ('frozen_original_files', 'api_secret_leak_paths'))
    result = {'checks': checks, 'passed': passed, 'extended_rows': len(rows),
              'branch': git('branch', '--show-current').decode().strip(),
              'head': git('rev-parse', 'HEAD').decode().strip(),
              'delivery_note': 'Local audit only; no GitHub push, repository rename, bonus or VLearn submission claimed.'}
    (ROOT / 'report/checkpoints/delivery_audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if passed else 1)


if __name__ == '__main__':
    main()
