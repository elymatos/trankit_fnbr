from typing import Any, List, Sequence, Tuple

from .domain import LexicalToken


class TrankitLemmaTypePredictor:
    def __init__(self, pipeline: Any, model_version: str) -> None:
        self.pipeline = pipeline
        self.model_version = model_version

    def predict(
        self, lexical_tokens: Sequence[LexicalToken], top_k: int
    ) -> Sequence[Sequence[Tuple[str, float]]]:
        result = self.pipeline.posdep([token.text for token in lexical_tokens], is_sent=True)
        raw_tokens = result.get("tokens", result)
        if len(raw_tokens) != len(lexical_tokens):
            raise ValueError("Trankit FNBr returned the wrong token count")
        predictions = []
        for raw in raw_tokens:
            candidates = raw.get("lemma_type_candidates")
            if candidates is None:
                raise RuntimeError("configured Trankit checkpoint has no lemma_type head")
            predictions.append([
                (candidate["type"], float(candidate["probability"]))
                for candidate in candidates[:top_k]
            ])
        return predictions
