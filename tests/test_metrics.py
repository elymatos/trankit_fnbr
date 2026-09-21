from trankit_fnbr.metrics import evaluate_lemma_types


def test_metrics_report_per_type_macro_sort_and_top_k() -> None:
    report = evaluate_lemma_types(
        gold=["event", "object", "polarity"],
        ranked_predictions=[
            ["event", "relation"],
            ["role", "object"],
            ["polarity", "focus"],
        ],
    )

    assert report["accuracy"] == 2 / 3
    assert report["top_2_recall"] == 1.0
    assert report["conceptual_procedural_f1"] == 1.0
    assert report["per_type"]["object"]["f1"] == 0.0
    assert report["confusion_matrix"]["object"]["role"] == 1
