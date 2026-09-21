from trankit_fnbr.domain import Lemma, ParsedToken, Pattern
from trankit_fnbr.lexical import LexicalProcessor
from trankit_fnbr.repository import InMemoryLexiconRepository


def token(token_id: int, text: str, upos: str, start: int, end: int) -> ParsedToken:
    return ParsedToken(token_id, text, text.lower(), upos, "_", "_", 0, "dep", start, end)


def test_processor_keeps_lattice_and_selects_longest_reviewed_mwe() -> None:
    repo = InMemoryLexiconRepository(
        revision="fixture-1",
        forms={
            "em": [Lemma(1, "em", "predication", "ADP")],
            "primeiro": [Lemma(2, "primeiro", "value", "ADJ")],
            "lugar": [Lemma(3, "lugar", "object", "NOUN")],
        },
        patterns=[
            Pattern(10, "em primeiro", "em primeiro", "connection", reviewed=True),
            Pattern(11, "em primeiro lugar", "em primeiro lugar", "connection", reviewed=True),
        ],
    )
    tokens = [
        token(1, "Em", "ADP", 0, 2),
        token(2, "primeiro", "ADJ", 3, 11),
        token(3, "lugar", "NOUN", 12, 17),
    ]

    result = LexicalProcessor(repo).process(tokens, language="pt")

    assert [item.text for item in result.selected] == ["Em primeiro lugar"]
    assert result.selected[0].selected_lemma.id == 11
    assert {(item.start_token, item.end_token) for item in result.lattice} == {
        (1, 1), (2, 2), (3, 3), (1, 2), (1, 3)
    }
    assert result.lexicon_revision == "fixture-1"


def test_processor_matches_variable_pos_pattern() -> None:
    repo = InMemoryLexiconRepository(
        revision="fixture-2",
        forms={"mil": [Lemma(2, "mil", "quantification", "NUM")]},
        patterns=[Pattern(20, "$number_mil", "{NUM} mil", "quantification")],
    )
    tokens = [token(1, "dois", "NUM", 0, 4), token(2, "mil", "NUM", 5, 8)]

    result = LexicalProcessor(repo).process(tokens, language="pt")

    assert [(item.text, item.selected_lemma.id) for item in result.selected] == [("dois mil", 20)]


def test_selection_uses_confirmed_source_precedence_for_overlaps() -> None:
    repo = InMemoryLexiconRepository(
        revision="fixture-3",
        forms={},
        patterns=[
            Pattern(30, "fixed", "a b c", "connection", source="fixed"),
            Pattern(31, "$construction", "a b", "connection", source="construction"),
        ],
    )
    tokens = [token(1, "a", "X", 0, 1), token(2, "b", "X", 2, 3), token(3, "c", "X", 4, 5)]

    result = LexicalProcessor(repo).process(tokens, language="pt")

    assert [
        (item.start_token, item.end_token, item.selected_lemma.id if item.selected_lemma else None)
        for item in result.selected
    ] == [(1, 2, 31), (3, 3, None)]


def test_processor_matches_optional_groups_and_pos_alternatives() -> None:
    repo = InMemoryLexiconRepository(
        revision="fixture-4",
        forms={},
        patterns=[Pattern(40, "number", "[{DET}] {NUM|NOUN}", "quantification")],
    )
    tokens = [token(1, "os", "DET", 0, 2), token(2, "dois", "NUM", 3, 7)]

    result = LexicalProcessor(repo).process(tokens, language="pt")

    assert [(item.text, item.selected_lemma.id) for item in result.selected] == [("os dois", 40)]


def test_processor_resolves_variable_references_and_repetition() -> None:
    repo = InMemoryLexiconRepository(
        revision="fixture-5",
        forms={},
        patterns=[
            Pattern(50, "$num", "{NUM}", "quantification"),
            Pattern(51, "number group", "{$num}+ mil", "quantification"),
        ],
    )
    tokens = [
        token(1, "dois", "NUM", 0, 4),
        token(2, "três", "NUM", 5, 9),
        token(3, "mil", "NUM", 10, 13),
    ]

    result = LexicalProcessor(repo).process(tokens, language="pt")

    assert any(
        item.text == "dois três mil" and item.selected_lemma.id == 51
        for item in result.lattice
    )
