import pytest

from trankit_fnbr.domain import Lemma, LexicalToken, ParsedToken
from trankit_fnbr.projection import ProjectionError, project_dependencies


def parsed(token_id, text, head, deprel):
    return ParsedToken(token_id, text, text.lower(), "X", "_", "_", head, deprel, 0, 0)


def lexical(identifier, text, components):
    return LexicalToken(identifier, text, components[0], components[-1], 0, 0, tuple(components))


def test_collapses_mwe_and_redirects_external_dependents() -> None:
    source = [
        parsed(1, "Ele", 5, "nsubj"),
        parsed(2, "em", 4, "case"),
        parsed(3, "primeiro", 4, "amod"),
        parsed(4, "lugar", 5, "advmod"),
        parsed(5, "chegou", 0, "root"),
        parsed(6, "cedo", 3, "advmod"),
    ]
    selected = [
        lexical("1", "Ele", [1]),
        lexical("mwe", "em primeiro lugar", [2, 3, 4]),
        lexical("5", "chegou", [5]),
        lexical("6", "cedo", [6]),
    ]

    projected = project_dependencies(source, selected)

    assert [(t.id, t.text, t.head, t.deprel) for t in projected] == [
        (1, "Ele", 3, "nsubj"),
        (2, "em primeiro lugar", 3, "advmod"),
        (3, "chegou", 0, "root"),
        (4, "cedo", 2, "advmod"),
    ]


def test_rejects_disconnected_or_cyclic_projection() -> None:
    source = [parsed(1, "a", 2, "dep"), parsed(2, "b", 1, "dep")]
    selected = [lexical("1", "a", [1]), lexical("2", "b", [2])]

    with pytest.raises(ProjectionError, match="root"):
        project_dependencies(source, selected)
