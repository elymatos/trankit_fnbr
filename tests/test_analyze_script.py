import json

from scripts import analyze


class FakePipeline:
    def analyze(self, sentence, top_k):
        return {"sentence": sentence, "top_k": top_k}


def test_analyze_script_prints_pipeline_result(monkeypatch, capsys) -> None:
    modes = []

    def build(predictor_mode):
        modes.append(predictor_mode)
        return FakePipeline()

    monkeypatch.setattr(analyze, "build_pipeline", build)

    analyze.main(["Ele chegou.", "--top-k", "2"])

    assert modes == ["lexical"]
    assert json.loads(capsys.readouterr().out) == {
        "sentence": "Ele chegou.",
        "top_k": 2,
    }
