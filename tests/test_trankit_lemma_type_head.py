from types import SimpleNamespace

import torch

from trankit.models.classifiers import PosDepClassifier
from trankit.utils.conll import DEPREL, FEATS, FNBR_TYPE, FNBR_TYPES, UPOS, XPOS


def config():
    vocabs = {
        UPOS: {"_": 0, "VERB": 1},
        XPOS: {"_": 0},
        FEATS: {"_": 0},
        DEPREL: {"_": 0, "root": 1},
        FNBR_TYPE: {label: index for index, label in enumerate(FNBR_TYPES)},
    }
    return SimpleNamespace(
        vocabs={"fixture": vocabs}, embedding_name="xlm-roberta-base",
        training=True, hidden_num=16, linear_dropout=0.0, linear_bias=1,
        linear_activation="relu", device=torch.device("cpu"),
    )


def test_posdep_classifier_has_independent_fnbr_head_with_top_k_probabilities() -> None:
    classifier = PosDepClassifier(config(), "fixture")
    batch = SimpleNamespace(
        word_num=[2],
        head_idxs=torch.tensor([[0, 1]]),
        word_mask=torch.tensor([[False, False, False]]),
        upos_ids=torch.tensor([[1, 1]]),
        upos_type_idxs=torch.tensor([1, 1]),
        xpos_type_idxs=torch.tensor([0, 0]),
        feats_type_idxs=torch.tensor([0, 0]),
        deprel_idxs=torch.tensor([[1, 1]]),
        lemma_type_idxs=torch.tensor([8, 0]),
    )
    word_reprs = torch.randn(1, 2, 768)
    cls_reprs = torch.randn(1, 1, 768)

    loss = classifier(batch, word_reprs, cls_reprs)
    predictions = classifier.predict(batch, word_reprs, cls_reprs)

    assert torch.isfinite(loss)
    classifier.config.lemma_type_only = True
    assert torch.isfinite(classifier(batch, word_reprs, cls_reprs))
    assert classifier.lemma_type_ffn.out_features == 15
    assert len(predictions[4][0]) == 2
    assert len(predictions[4][0][0]) == 15
    assert {candidate["type"] for candidate in predictions[4][0][0]} <= set(FNBR_TYPES)
    assert all(0.0 <= candidate["probability"] <= 1.0 for candidate in predictions[4][0][0])
