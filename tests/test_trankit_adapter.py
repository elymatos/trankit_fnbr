from trankit_fnbr.trankit_adapter import TrankitUDParser


class FakeTrankit:
    def __call__(self, text):
        return {"sentences": [{"tokens": [
            {"id": 1, "text": "Não", "lemma": "não", "upos": "ADV", "xpos": "_", "feats": "_", "head": 2, "deprel": "advmod", "span": (0, 3)},
            {"id": 2, "text": "chegou", "lemma": "chegar", "upos": "VERB", "xpos": "_", "feats": "_", "head": 0, "deprel": "root", "span": (4, 10)},
        ]}]}


def test_adapter_maps_trankit_output_to_source_tokens() -> None:
    parser = TrankitUDParser(FakeTrankit(), model_version="fixture")

    sentences = parser.parse("Não chegou")

    assert parser.model_version == "fixture"
    assert [(token.id, token.start_char, token.end_char, token.head) for token in sentences[0]] == [
        (1, 0, 3, 2), (2, 4, 10, 0)
    ]


def test_adapter_preserves_contractions_and_collapses_expanded_dependencies() -> None:
    class ContractionTrankit:
        def __call__(self, text):
            return {"sentences": [{"tokens": [
                {"id": [1, 2], "text": "Pelo", "dspan": [0, 4], "expanded": [
                    {"id": 1, "text": "por", "upos": "ADP", "head": 3, "deprel": "case", "lemma": "por"},
                    {"id": 2, "text": "o", "upos": "DET", "head": 3, "deprel": "det", "lemma": "o"},
                ]},
                {"id": 3, "text": "menos", "upos": "ADV", "head": 4, "deprel": "advmod", "lemma": "menos", "dspan": [5, 10]},
                {"id": 4, "text": "chegou", "upos": "VERB", "head": 0, "deprel": "root", "lemma": "chegar", "dspan": [11, 17]},
            ]}]}

    sentence = TrankitUDParser(ContractionTrankit()).parse("Pelo menos chegou")[0]

    assert [(token.id, token.text, token.head, token.deprel) for token in sentence] == [
        (1, "Pelo", 3, "case"),
        (3, "menos", 4, "advmod"),
        (4, "chegou", 0, "root"),
    ]
