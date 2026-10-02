from trankit.utils.base_utils import get_output_doc
from trankit.utils.conll import FNBR_TYPE_CANDIDATES


def test_posdep_output_preserves_ranked_fnbr_types() -> None:
    ranking = [{"type": "event", "probability": 0.9}]
    sentence = [{"tokens": [{"id": 1, "text": "chegou"}]}]
    conllu_doc = {0: {"mwts": [], 1: {
        "id": 1, "text": "chegou", "head": 0, "deprel": "root",
        FNBR_TYPE_CANDIDATES: ranking,
    }}}

    result = get_output_doc(sentence, conllu_doc)

    assert result[0]["tokens"][0][FNBR_TYPE_CANDIDATES] == ranking
