from sqlalchemy import create_engine

from trankit_fnbr.database import MariaDBLexiconRepository, UnsupportedSchemaError


def fixture_engine():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE language (idLanguage INTEGER PRIMARY KEY, language TEXT)")
        connection.exec_driver_sql("CREATE TABLE namespace (idNamespace INTEGER PRIMARY KEY, entry TEXT, scope TEXT)")
        connection.exec_driver_sql("CREATE TABLE udpos (idUDPOS INTEGER PRIMARY KEY, POS TEXT)")
        connection.exec_driver_sql("CREATE TABLE lexicon (idLexicon INTEGER PRIMARY KEY, form TEXT)")
        connection.exec_driver_sql("CREATE TABLE lemma_form (idLemma INTEGER, idLexicon INTEGER)")
        connection.exec_driver_sql("""CREATE TABLE lemma (
            idLemma INTEGER PRIMARY KEY, name TEXT, idLanguage INTEGER, idLexicon INTEGER,
            idNamespace INTEGER, idUDPOS INTEGER, pattern TEXT, compiledPattern TEXT
        )""")
        connection.exec_driver_sql("INSERT INTO language VALUES (1, 'pt')")
        connection.exec_driver_sql("INSERT INTO namespace VALUES (10, 'nsp_lemma_connection', 'lemma')")
        connection.exec_driver_sql("INSERT INTO udpos VALUES (20, 'ADV')")
        connection.exec_driver_sql("INSERT INTO lexicon VALUES (30, 'portanto')")
        connection.exec_driver_sql("INSERT INTO lemma VALUES (40, 'portanto', 1, 30, 10, 20, NULL, NULL)")
        connection.exec_driver_sql("INSERT INTO lemma_form VALUES (40, 30)")
        connection.exec_driver_sql("INSERT INTO lemma VALUES (41, 'em primeiro lugar', 1, 30, 10, 20, 'em primeiro lugar', NULL)")
    return engine


def test_repository_reads_typed_lemmas_and_patterns() -> None:
    repository = MariaDBLexiconRepository(fixture_engine(), revision="snapshot-7")

    assert [(lemma.id, lemma.lemma_type, lemma.upos) for lemma in repository.lemmas_for("Portanto", "ADV", "pt")] == [
        (40, "connection", "ADV")
    ]
    assert [(pattern.lemma_id, pattern.expression) for pattern in repository.patterns("pt")] == [
        (41, "em primeiro lugar")
    ]
    assert repository.revision == "snapshot-7"


def test_repository_fails_fast_for_unsupported_schema() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE lemma (idLemma INTEGER PRIMARY KEY)")

    try:
        MariaDBLexiconRepository(engine, revision="broken")
    except UnsupportedSchemaError as error:
        assert "lemma" in str(error)
    else:
        raise AssertionError("unsupported schema was accepted")
