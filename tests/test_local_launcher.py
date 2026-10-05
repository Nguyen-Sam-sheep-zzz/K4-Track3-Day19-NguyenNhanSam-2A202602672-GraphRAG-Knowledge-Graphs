from unittest.mock import patch
from scripts.run_local import pace_embeddings


def test_gemini_batch_pacing_counts_texts_not_http_requests():
    with patch('scripts.run_local.time.sleep') as sleep:
        pace_embeddings('gemini', 16)
    sleep.assert_called_once_with(11.2)


def test_other_embedding_provider_has_no_gemini_delay():
    with patch('scripts.run_local.time.sleep') as sleep:
        pace_embeddings('openai', 16)
    sleep.assert_not_called()
