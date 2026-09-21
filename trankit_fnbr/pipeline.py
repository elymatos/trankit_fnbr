from typing import Any, Dict, List, Protocol, Sequence, Tuple

from .domain import LexicalToken, ParsedToken
from .lexical import LexicalProcessor
from .projection import project_dependencies


class UDParser(Protocol):
    model_version: str

    def parse(self, text: str) -> Sequence[Sequence[ParsedToken]]:
        ...


class LemmaTypePredictor(Protocol):
    model_version: str

    def predict(
        self, lexical_tokens: Sequence[LexicalToken], top_k: int
    ) -> Sequence[Sequence[Tuple[str, float]]]:
        ...


class LexicalPriorPredictor:
    """Explicit baseline used before a trained contextual checkpoint is configured."""

    model_version = "lexical-prior-baseline"

    def predict(
        self, lexical_tokens: Sequence[LexicalToken], top_k: int
    ) -> Sequence[Sequence[Tuple[str, float]]]:
        predictions = []
        for token in lexical_tokens:
            types = sorted({lemma.lemma_type for lemma in token.lemma_candidates if lemma.lemma_type})
            probability = 1.0 / len(types) if types else 0.0
            predictions.append([(lemma_type, probability) for lemma_type in types[:top_k]])
        return predictions


class AnalysisPipeline:
    def __init__(
        self,
        parser: UDParser,
        lexical_processor: LexicalProcessor,
        type_predictor: LemmaTypePredictor,
        database_schema_version: str,
    ) -> None:
        self.parser = parser
        self.lexical_processor = lexical_processor
        self.type_predictor = type_predictor
        self.database_schema_version = database_schema_version

    def analyze(self, text: str, top_k: int = 3) -> Dict[str, Any]:
        sentences = []
        for parsed_tokens in self.parser.parse(text):
            lexical = self.lexical_processor.process(parsed_tokens)
            projected = project_dependencies(parsed_tokens, lexical.selected)
            predictions = self.type_predictor.predict(lexical.selected, top_k)
            if len(predictions) != len(projected):
                raise ValueError("lemma-type predictor returned the wrong token count")
            tokens = []
            for dependency, lexical_token, candidates in zip(projected, lexical.selected, predictions):
                tokens.append({
                    "id": dependency.id,
                    "lexical_token_id": lexical_token.id,
                    "text": lexical_token.text,
                    "selected_lemma_id": (
                        lexical_token.selected_lemma.id if lexical_token.selected_lemma else None
                    ),
                    "lemma_candidates": [lemma.id for lemma in lexical_token.lemma_candidates],
                    "lemma_type_candidates": [
                        {"type": lemma_type, "probability": probability}
                        for lemma_type, probability in candidates[:top_k]
                    ],
                    "head": dependency.head,
                    "deprel": dependency.deprel,
                    "source_token_ids": list(dependency.source_token_ids),
                    "start_char": lexical_token.start_char,
                    "end_char": lexical_token.end_char,
                })
            sentences.append({
                "tokens": tokens,
                "lattice": [self._lattice_item(candidate) for candidate in lexical.lattice],
            })
        return {
            "model_version": self.type_predictor.model_version,
            "parser_model_version": self.parser.model_version,
            "lexical_policy_version": self.lexical_processor.policy_version,
            "database_schema_version": self.database_schema_version,
            "lexicon_revision": self.lexical_processor.repository.revision,
            "sentences": sentences,
        }

    @staticmethod
    def _lattice_item(candidate: LexicalToken) -> Dict[str, Any]:
        return {
            "id": candidate.id,
            "text": candidate.text,
            "start_token": candidate.start_token,
            "end_token": candidate.end_token,
            "start_char": candidate.start_char,
            "end_char": candidate.end_char,
            "source_token_ids": list(candidate.components),
            "lemma_candidates": [lemma.id for lemma in candidate.lemma_candidates],
            "source": candidate.source,
            "reviewed": candidate.reviewed,
        }
