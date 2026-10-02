from typing import Any, List, Sequence, Tuple

from .domain import LexicalToken


class TrankitLemmaTypePredictor:
    def __init__(self, pipeline: Any, model_version: str) -> None:
        self.pipeline = pipeline
        self.model_version = model_version

    def predict(
        self, lexical_tokens: Sequence[LexicalToken], top_k: int
    ) -> Sequence[Sequence[Tuple[str, float]]]:
        predictions, _ = self._analyze(lexical_tokens, top_k, require_scaffold=False)
        return predictions

    def predict_with_scaffold(
        self, lexical_tokens: Sequence[LexicalToken], top_k: int
    ) -> Tuple[List[List[Tuple[str, float]]], List[Tuple[int, str]]]:
        return self._analyze(lexical_tokens, top_k, require_scaffold=True)

    def _analyze(
        self, lexical_tokens: Sequence[LexicalToken], top_k: int, require_scaffold: bool
    ) -> Tuple[List[List[Tuple[str, float]]], List[Tuple[int, str]]]:
        result = self.pipeline.posdep([token.text for token in lexical_tokens], is_sent=True)
        raw_tokens = result.get("tokens", result)
        if len(raw_tokens) != len(lexical_tokens):
            raise ValueError("Trankit FNBr returned the wrong token count")
        predictions = []
        scaffold = []
        for raw in raw_tokens:
            candidates = raw.get("lemma_type_candidates")
            if candidates is None:
                raise RuntimeError("configured Trankit checkpoint has no lemma_type head")
            predictions.append([
                (candidate["type"], float(candidate["probability"]))
                for candidate in candidates[:top_k]
            ])
            if require_scaffold:
                scaffold.append((int(raw["head"]), str(raw["deprel"])))
        return predictions, scaffold
