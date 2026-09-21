from trankit_fnbr.domain import Lemma, ParsedToken, Pattern
from trankit_fnbr.lexical import LexicalProcessor
from trankit_fnbr.pipeline import AnalysisPipeline
from trankit_fnbr.repository import InMemoryLexiconRepository


class FakeParser:
    model_version = "parser-fixture"

    def parse(self, text):
        return [[
            ParsedToken(1, "Não", "não", "ADV", "_", "_", 2, "advmod", 0, 3),
            ParsedToken(2, "chegou", "chegar", "VERB", "_", "_", 0, "root", 4, 10),
        ]]


class FakeTypePredictor:
    model_version = "type-fixture"

    def predict(self, lexical_tokens, top_k):
        return [
            [("polarity", 0.8), ("focus", 0.2)],
            [("event", 0.9), ("relation", 0.1)],
        ]


def test_pipeline_orchestrates_parse_lookup_selection_typing_and_projection() -> None:
    repository = InMemoryLexiconRepository(
        revision="r1",
        forms={
            "não": [Lemma(1, "não", "polarity", "ADV")],
            "chegou": [Lemma(2, "chegar", "event", "VERB")],
        },
        patterns=[],
    )
    pipeline = AnalysisPipeline(
        parser=FakeParser(),
        lexical_processor=LexicalProcessor(repository),
        type_predictor=FakeTypePredictor(),
        database_schema_version="webtool45",
    )

    result = pipeline.analyze("Não chegou", top_k=2)

    assert result["model_version"] == "type-fixture"
    assert result["parser_model_version"] == "parser-fixture"
    assert result["lexicon_revision"] == "r1"
    assert result["sentences"][0]["tokens"][0]["lexical_type"] == "polarity"
    assert result["sentences"][0]["tokens"][0]["lemma_type_candidates"] == [
        {"type": "polarity", "probability": 0.8},
        {"type": "focus", "probability": 0.2},
    ]
    assert result["sentences"][0]["tokens"][1]["head"] == 0
