"""Run the unmodified lab grader with the project's .env, plus a separate audit.

Usage: python scripts/run_local.py bench_kg.py --judge
Only this child process overrides inherited provider configuration.
"""
from __future__ import annotations
import json
import os
import runpy
import sys
import time
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def pace_embeddings(provider, text_count):
    # Gemini's free-tier RPM counts each text in a batch, not just HTTP requests.
    if provider == 'gemini':
        time.sleep(0.7 * text_count)


def main():
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    for key in list(os.environ):
        if key.startswith(('OPENAI_', 'OPENROUTER_', 'GEMINI_', 'ANTHROPIC_', 'NEO4J_')) or key in (
                'LLM_PROVIDER', 'EMBEDDING_PROVIDER', 'LAB_SOLUTION_PACKAGE'):
            os.environ.pop(key, None)
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env', override=True)
    import src.llm as module
    instances = []
    original = module.MeteredLLM
    target = sys.argv[1] if len(sys.argv) > 1 else 'bench_kg.py'
    suffix = 'check' if '--check' in sys.argv else 'build' if '--build' in sys.argv else 'benchmark'
    audit_dir = ROOT / 'report' / 'checkpoints'
    audit_dir.mkdir(parents=True, exist_ok=True)
    run_id = time.strftime('%Y%m%d-%H%M%S')

    def save_audit(llm):
        audit = {'run_id': run_id, 'chat_model': llm.chat_model, 'embedding_model': llm.embedding_model,
                 'usage': asdict(llm.usage), 'calls': llm.records,
                 'cost_note': 'usd is the priced subtotal; embedding cost/usage unknown when null; not a bill.'}
        data = json.dumps(audit, ensure_ascii=False, indent=2)
        (audit_dir / f'{Path(target).stem}_{suffix}_{run_id}.json').write_text(data, encoding='utf-8')
        (audit_dir / f'{Path(target).stem}_{suffix}_audit_0.json').write_text(data, encoding='utf-8')

    class AuditedLLM(original):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            instances.append(self)

        def chat(self, *args, **kwargs):
            result = super().chat(*args, **kwargs)
            save_audit(self)
            print(f'[audit] chat {len(self.records)} saved', flush=True)
            return result

        def embed(self, text):
            # Below Gemini free-tier 100 requests/minute; benchmark remains a cold API run.
            pace_embeddings(self.embed_provider, 1)
            result = super().embed(text)
            save_audit(self)
            return result

        def embed_many(self, texts):
            pace_embeddings(self.embed_provider, len(texts))
            result = super().embed_many(texts)
            save_audit(self)
            return result

    module.MeteredLLM = AuditedLLM
    sys.argv = [target, *sys.argv[2:]]
    try:
        runpy.run_path(str(ROOT / target), run_name='__main__')
    finally:
        suffix = 'check' if '--check' in sys.argv else 'build' if '--build' in sys.argv else 'benchmark'
        audit_dir = ROOT / 'report' / 'checkpoints'
        audit_dir.mkdir(parents=True, exist_ok=True)
        assets = {}
        for i, llm in enumerate(instances):
            audit = {'chat_model': llm.chat_model, 'embedding_model': llm.embedding_model,
                     'usage': asdict(llm.usage), 'calls': llm.records,
                     'cost_note': 'usd is the priced subtotal; embedding cost/usage unknown when null; not a bill.'}
            (audit_dir / f'{Path(target).stem}_{suffix}_audit_{i}.json').write_text(
                json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
            assets.update(llm.embedding_assets)
        if assets:
            cache = ROOT / '.cache'
            cache.mkdir(exist_ok=True)
            cache_path = cache / f'{Path(target).stem}_{suffix}_embeddings.json'
            previous = json.loads(cache_path.read_text(encoding='utf-8')) if cache_path.exists() else {}
            merged = previous.get('vectors', {}) if previous.get('model') == instances[0].embedding_model else {}
            merged.update(assets)
            cache_path.write_text(
                json.dumps({'model': instances[0].embedding_model, 'vectors': merged}, ensure_ascii=False),
                encoding='utf-8')


if __name__ == '__main__':
    main()
