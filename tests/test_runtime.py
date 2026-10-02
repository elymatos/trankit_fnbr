import hashlib
import json

import pytest

from trankit_fnbr import runtime


class FakePipeline:
    def analyze(self, text, top_k):
        return {"text": text, "top_k": top_k}


def test_lazy_pipeline_uses_configured_predictor_mode(monkeypatch) -> None:
    modes = []
    monkeypatch.setenv("FNBR_PREDICTOR_MODE", "lexical")

    def build(predictor_mode="model"):
        modes.append(predictor_mode)
        return FakePipeline()

    monkeypatch.setattr(runtime, "build_pipeline", build)

    result = runtime.LazyConfiguredPipeline().analyze("texto", top_k=2)

    assert modes == ["lexical"]
    assert result == {"text": "texto", "top_k": 2}


def test_readiness_checks_database_without_running_inference(monkeypatch) -> None:
    class Repository:
        revision = "fixture-revision"
        called = 0

        def check_connection(self):
            self.called += 1

    class Configured:
        lexical_processor = type("Lexical", (), {"repository": Repository()})()
        type_predictor = type("Predictor", (), {"model_version": "joint-fixture"})()
        scaffold_source = "model"
        database_schema_version = "webtool45"

    monkeypatch.setattr(runtime, "build_pipeline", lambda predictor_mode: Configured())
    lazy = runtime.LazyConfiguredPipeline()
    assert lazy.ready() == {
        "status": "ready", "model_version": "joint-fixture", "scaffold_source": "model",
        "database_schema_version": "webtool45", "lexicon_revision": "fixture-revision",
    }
    assert lazy._pipeline.lexical_processor.repository.called == 1


def test_model_scaffold_requires_matching_joint_checkpoint(tmp_path) -> None:
    model_dir = tmp_path / "xlm-roberta-large" / "customized"
    model_dir.mkdir(parents=True)
    checkpoint = model_dir / "customized.tagger.mdl"
    checkpoint.write_bytes(b"checkpoint")
    metadata_path = model_dir / "fnbr.training.json"
    metadata = {"objectives": "type_only", "checkpoint_sha256": hashlib.sha256(b"checkpoint").hexdigest()}
    metadata_path.write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="jointly trained"):
        runtime.require_joint_checkpoint(str(tmp_path), "xlm-roberta-large", "customized")
    metadata["objectives"] = "joint"
    metadata_path.write_text(json.dumps(metadata))
    runtime.require_joint_checkpoint(str(tmp_path), "xlm-roberta-large", "customized")
    checkpoint.write_bytes(b"changed")
    with pytest.raises(ValueError, match="does not match"):
        runtime.require_joint_checkpoint(str(tmp_path), "xlm-roberta-large", "customized")
