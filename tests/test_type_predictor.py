from trankit_fnbr.domain import LexicalToken
from trankit_fnbr.type_predictor import TrankitLemmaTypePredictor


class FakeTrankit:
    def posdep(self, words, is_sent):
        assert words == ["não", "chegou"]
        assert is_sent is True
        return {"tokens": [
            {"text": "não", "head": 2, "deprel": "advmod", "lemma_type_candidates": [
                {"type": "polarity", "probability": 0.8},
                {"type": "focus", "probability": 0.15},
                {"type": "connection", "probability": 0.05},
            ]},
            {"text": "chegou", "head": 0, "deprel": "root", "lemma_type_candidates": [
                {"type": "event", "probability": 0.9},
                {"type": "relation", "probability": 0.1},
            ]},
        ]}


class TypeOnlyTrankit(FakeTrankit):
    def posdep(self, words, is_sent):
        result = super().posdep(words, is_sent)
        for token in result["tokens"]:
            token.pop("deprel")
        return result


def lexical(identifier, text):
    return LexicalToken(identifier, text, int(identifier), int(identifier), 0, 0, (int(identifier),))


def test_predictor_exposes_requested_top_k_probabilities() -> None:
    predictor = TrankitLemmaTypePredictor(FakeTrankit(), model_version="fnbr-fixture")

    predictions = predictor.predict([lexical("1", "não"), lexical("2", "chegou")], top_k=2)

    assert predictions == [
        [("polarity", 0.8), ("focus", 0.15)],
        [("event", 0.9), ("relation", 0.1)],
    ]
    assert predictor.predict_with_scaffold(
        [lexical("1", "não"), lexical("2", "chegou")], top_k=2
    )[1] == [(2, "advmod"), (0, "root")]
    assert TrankitLemmaTypePredictor(TypeOnlyTrankit(), "type-only").predict(
        [lexical("1", "não"), lexical("2", "chegou")], top_k=1
    )[0] == [("polarity", 0.8)]
