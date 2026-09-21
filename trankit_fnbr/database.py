from typing import Dict, Optional, Sequence, Tuple

from sqlalchemy import Engine, bindparam, inspect, text

from .domain import Lemma, Pattern


class UnsupportedSchemaError(RuntimeError):
    pass


def _canonical_lemma_type(value: Optional[str]) -> Optional[str]:
    prefix = "nsp_lemma_"
    if value and value.startswith(prefix):
        return value[len(prefix):]
    return value


_REQUIRED_COLUMNS = {
    "language": {"idLanguage", "language"},
    "namespace": {"idNamespace", "entry", "scope"},
    "udpos": {"idUDPOS", "POS"},
    "lexicon": {"idLexicon", "form"},
    "lemma_form": {"idLemma", "idLexicon"},
    "lemma": {
        "idLemma", "name", "idLanguage", "idNamespace", "idUDPOS",
        "pattern", "compiledPattern",
    },
}


class MariaDBLexiconRepository:
    """Read-only adapter for the WebTool 4.5 lexical schema.

    The adapter accepts any SQLAlchemy engine so its SQL contract can be tested
    against an isolated fixture. Production configuration must use a read-only
    MariaDB account.
    """

    schema_version = "webtool45"

    def __init__(self, engine: Engine, revision: str) -> None:
        if not revision.strip():
            raise ValueError("FNBr lexicon revision is required")
        self.engine = engine
        self._revision = revision
        self._patterns: Dict[str, Tuple[Pattern, ...]] = {}
        self._validate_schema()

    @property
    def revision(self) -> str:
        return self._revision

    def _validate_schema(self) -> None:
        inspector = inspect(self.engine)
        errors = []
        tables = set(inspector.get_table_names())
        for table, required in _REQUIRED_COLUMNS.items():
            if table not in tables:
                errors.append("missing table {}".format(table))
                continue
            actual = {column["name"] for column in inspector.get_columns(table)}
            missing = required - actual
            if missing:
                errors.append("{} missing {}".format(table, ", ".join(sorted(missing))))
        if errors:
            raise UnsupportedSchemaError("Unsupported FNBr schema: " + "; ".join(errors))

    def lemmas_for(self, form: str, upos: str, language: str) -> Sequence[Lemma]:
        statement = text("""
            SELECT DISTINCT lm.idLemma, lm.name, ns.entry AS lemma_type, up.POS AS upos
            FROM lexicon AS lx
            JOIN lemma_form AS lf ON lf.idLexicon = lx.idLexicon
            JOIN lemma AS lm ON lm.idLemma = lf.idLemma
            JOIN language AS lang ON lang.idLanguage = lm.idLanguage
            LEFT JOIN namespace AS ns
                ON ns.idNamespace = lm.idNamespace AND ns.scope = 'lemma'
            LEFT JOIN udpos AS up ON up.idUDPOS = lm.idUDPOS
            WHERE lower(lx.form) = lower(:form) AND lang.language = :language
            ORDER BY CASE WHEN up.POS = :upos THEN 0 ELSE 1 END, lm.idLemma
        """)
        with self.engine.connect() as connection:
            rows = connection.execute(
                statement, {"form": form, "language": language, "upos": upos}
            ).mappings().all()
        candidates = tuple(Lemma(
            int(row["idLemma"]), row["name"],
            _canonical_lemma_type(row["lemma_type"]), row["upos"]
        ) for row in rows)
        matching = tuple(lemma for lemma in candidates if lemma.upos in (None, upos))
        return matching or candidates

    def patterns(self, language: str) -> Sequence[Pattern]:
        if language in self._patterns:
            return self._patterns[language]
        statement = text("""
            SELECT lm.idLemma, lm.name, lm.pattern, ns.entry AS lemma_type
            FROM lemma AS lm
            JOIN language AS lang ON lang.idLanguage = lm.idLanguage
            LEFT JOIN namespace AS ns
                ON ns.idNamespace = lm.idNamespace AND ns.scope = 'lemma'
            WHERE lang.language = :language
              AND lm.pattern IS NOT NULL AND lm.pattern <> ''
            ORDER BY lm.idLemma
        """)
        with self.engine.connect() as connection:
            rows = connection.execute(statement, {"language": language}).mappings().all()
        patterns = tuple(Pattern(
            int(row["idLemma"]), row["name"], row["pattern"],
            _canonical_lemma_type(row["lemma_type"]), reviewed=True
        ) for row in rows)
        self._patterns[language] = patterns
        return patterns
