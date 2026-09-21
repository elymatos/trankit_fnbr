import json

import pytest

from scripts import analyze


class FakePipeline:
    def analyze(self, sentence, top_k):
        print("analyzer diagnostic")
        return {"sentence": sentence, "top_k": top_k}


def test_analyze_script_prints_pipeline_result(monkeypatch, capsys) -> None:
    monkeypatch.setenv("FNBR_DATABASE_URL", "mysql+pymysql://fixture")
    monkeypatch.setenv("FNBR_LEXICON_REVISION", "fixture")
    modes = []

    def build(predictor_mode):
        modes.append(predictor_mode)
        print("loader diagnostic")
        return FakePipeline()

    monkeypatch.setattr(analyze, "build_pipeline", build)

    analyze.main(["Ele chegou.", "--top-k", "2"])

    assert modes == ["lexical"]
    captured = capsys.readouterr()
    assert json.loads(captured.out) == {
        "sentence": "Ele chegou.",
        "top_k": 2,
    }
    assert "loader diagnostic" in captured.err
    assert "analyzer diagnostic" in captured.err


def test_analyze_script_explains_missing_database_configuration(
    monkeypatch, capsys
) -> None:
    monkeypatch.delenv("FNBR_DATABASE_URL", raising=False)
    monkeypatch.delenv("FNBR_LEXICON_REVISION", raising=False)
    monkeypatch.setattr(analyze, "load_dotenv", lambda *args, **kwargs: False)

    with pytest.raises(SystemExit) as error:
        analyze.main(["Ele chegou."])

    assert error.value.code == 2
    message = capsys.readouterr().err
    assert "FNBR_DATABASE_URL" in message
    assert "FNBR_LEXICON_REVISION" in message
    assert "cp .env.example .env" in message
