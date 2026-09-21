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
