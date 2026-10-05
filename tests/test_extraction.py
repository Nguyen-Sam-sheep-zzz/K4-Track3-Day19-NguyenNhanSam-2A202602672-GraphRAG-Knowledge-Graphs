import pytest
from src.graph import extract_news_cases
from src.models import Document


@pytest.mark.parametrize('response', ['bad json', '{"cases":{}}', '{"cases":[{"people":"bad"}]}'])
def test_invalid_extraction_is_reported_with_source(response):
    with pytest.raises(ValueError, match='news-test'):
        extract_news_cases(Document('news-test', 'tin'), lambda _: response, [])

