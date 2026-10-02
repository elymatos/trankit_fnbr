from fastapi.testclient import TestClient

from trankit_fnbr.api import create_app


class FakePipeline:
    def analyze(self, text, top_k=3):
        assert text == "Em primeiro lugar, chegou."
        assert top_k == 2
        return {
            "model_version": "fixture-model",
            "lexical_policy_version": "1",
            "database_schema_version": "webtool45",
            "lexicon_revision": "snapshot-9",
            "sentences": [{
                "tokens": [{
                    "id": 1,
                    "text": "Em primeiro lugar",
                    "selected_lemma_id": 8,
                    "lemma_type_candidates": [{"type": "connection", "probability": 0.9}],
                    "head": 2,
                    "deprel": "advmod",
                    "source_token_ids": [1, 2, 3],
                    "start_char": 0,
                    "end_char": 17,
                }],
                "lattice": [],
            }],
        }


def test_raw_text_endpoint_returns_versioned_fnbr_analysis() -> None:
    client = TestClient(create_app(FakePipeline()))

    response = client.post("/fnbr/", json={"text": "Em primeiro lugar, chegou.", "top_k": 2})

    assert response.status_code == 200
    payload = response.json()
    assert payload["lexicon_revision"] == "snapshot-9"
    assert payload["sentences"][0]["tokens"][0]["selected_lemma_id"] == 8


def test_health_endpoints_do_not_run_analysis() -> None:
    class ReadyPipeline(FakePipeline):
        def ready(self):
            return {"status": "ready", "model_version": "joint-fixture"}

    client = TestClient(create_app(ReadyPipeline()))
    assert client.get("/health/live").json() == {"status": "alive"}
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["model_version"] == "joint-fixture"


def test_readiness_returns_503_without_exposing_database_errors() -> None:
    class UnavailablePipeline(FakePipeline):
        def ready(self):
            raise ConnectionError("secret database host")

    client = TestClient(create_app(UnavailablePipeline()))
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert "secret" not in response.text


def test_raw_text_endpoint_rejects_blank_text() -> None:
    client = TestClient(create_app(FakePipeline()))

    response = client.post("/fnbr/", json={"text": "   "})

    assert response.status_code == 422
