import math
from types import SimpleNamespace

import pytest

from src.llm import MeteredLLM, Usage, price


def test_unknown_price_is_not_free():
    assert math.isnan(price('unknown-model', 1000))


def test_luna_reference_price():
    assert price('gpt-6-luna', 1_000_000, 1_000_000) == pytest.approx(0.6)


def test_missing_embedding_usage_is_marked():
    llm = MeteredLLM.__new__(MeteredLLM)
    llm.embed_model_id = 'gemini-embedding-001'
    llm.embedding_model = 'gemini:gemini-embedding-001'
    llm.usage = Usage()
    llm.records = []
    llm._embed_client = SimpleNamespace(embeddings=SimpleNamespace(
        create=lambda **kwargs: SimpleNamespace(
            usage=None, data=[SimpleNamespace(embedding=[1.0, 0.0])])) )
    assert llm.embed('ma túy') == [1.0, 0.0]
    assert llm.usage.missing_usage_calls == 1
    assert llm.usage.unpriced_calls == 1
    assert llm.records[0]['usd'] is None


def test_batch_embedding_accepts_gemini_missing_zero_index():
    llm = MeteredLLM.__new__(MeteredLLM)
    llm.embed_model_id = 'gemini-embedding-001'
    llm.embedding_model = 'gemini:gemini-embedding-001'
    llm.usage, llm.records, llm.embedding_assets = Usage(), [], {}
    llm._embed_client = SimpleNamespace(embeddings=SimpleNamespace(create=lambda **kw:
        SimpleNamespace(usage=None, data=[SimpleNamespace(index=None, embedding=[1., 0.]),
                                          SimpleNamespace(index=1, embedding=[0., 1.])])) )
    assert llm.embed_many(['one', 'two']) == [[1., 0.], [0., 1.]]
