from app.services import semantic_intent_ai as semantic_ai


class _Response:
    def __init__(self, status_code: int, text: str = "", headers=None):
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}
        self.ok = 200 <= status_code < 300


def test_semantic_ai_retries_429_using_server_retry_window(monkeypatch):
    responses = [
        _Response(
            429,
            'Rate limit reached. Please try again in 2.623s.',
        ),
        _Response(200, '{}'),
    ]
    sleeps = []

    monkeypatch.setenv("OPTIME_SEMANTIC_AI_MAX_ATTEMPTS", "3")
    monkeypatch.setattr(semantic_ai.requests, "post", lambda *args, **kwargs: responses.pop(0))
    monkeypatch.setattr(semantic_ai.time, "sleep", lambda seconds: sleeps.append(seconds))

    response = semantic_ai._request_with_retry("https://example.test/responses", {}, {})

    assert response.status_code == 200
    assert sleeps == [2.873]


def test_semantic_ai_does_not_retry_non_transient_http_error(monkeypatch):
    calls = []

    def _post(*args, **kwargs):
        calls.append(1)
        return _Response(400, 'bad request')

    monkeypatch.setenv("OPTIME_SEMANTIC_AI_MAX_ATTEMPTS", "3")
    monkeypatch.setattr(semantic_ai.requests, "post", _post)

    response = semantic_ai._request_with_retry("https://example.test/responses", {}, {})

    assert response.status_code == 400
    assert len(calls) == 1
