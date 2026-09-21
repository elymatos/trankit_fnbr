from dataclasses import dataclass, field
from typing import List, Optional, Tuple


LEMMA_TYPES = (
    "event", "object", "role", "relation", "quality", "value",
    "reference", "quantification", "polarity", "degree", "modality",
    "connection", "focus", "predication", "interaction",
)


@dataclass(frozen=True)
class Lemma:
    id: int
    name: str
    lemma_type: Optional[str]
    upos: Optional[str] = None

    def __post_init__(self) -> None:
        if self.lemma_type is not None and self.lemma_type not in LEMMA_TYPES:
            raise ValueError("Unknown FNBr lemma type: {}".format(self.lemma_type))


@dataclass(frozen=True)
class Pattern:
    lemma_id: int
    name: str
    expression: str
    lemma_type: Optional[str]
    reviewed: bool = False
    source: str = "variable"

    @property
    def lemma(self) -> Lemma:
        return Lemma(self.lemma_id, self.name, self.lemma_type, "X")


@dataclass(frozen=True)
class ParsedToken:
    id: int
    text: str
    lemma: str
    upos: str
    xpos: str
    feats: str
    head: int
    deprel: str
    start_char: int
    end_char: int


@dataclass(frozen=True)
class LexicalToken:
    id: str
    text: str
    start_token: int
    end_token: int
    start_char: int
    end_char: int
    components: Tuple[int, ...]
    lemma_candidates: Tuple[Lemma, ...] = field(default_factory=tuple)
    selected_lemma: Optional[Lemma] = None
    source: str = "ordinary"
    reviewed: bool = False


@dataclass(frozen=True)
class LexicalAnalysis:
    lattice: Tuple[LexicalToken, ...]
    selected: Tuple[LexicalToken, ...]
    lexicon_revision: str
    policy_version: str = "1"
