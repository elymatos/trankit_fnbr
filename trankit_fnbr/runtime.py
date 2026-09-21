import os
import threading
from typing import Any, Dict, Optional

from sqlalchemy import create_engine, event
from sqlalchemy.exc import SQLAlchemyError

from .database import MariaDBLexiconRepository
from .lexical import LexicalProcessor
from .pipeline import AnalysisPipeline, LemmaTypePredictor, LexicalPriorPredictor
from .trankit_adapter import TrankitUDParser
from .type_predictor import TrankitLemmaTypePredictor


UPSTREAM_TRANKIT_REVISION = "54e863327391262cf72f6adc1b0ff104e972a1dc"


def create_read_only_engine(database_url: str):
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=int(os.getenv("FNBR_DB_POOL_SIZE", "5")),
        pool_recycle=int(os.getenv("FNBR_DB_POOL_RECYCLE_SECONDS", "1800")),
        connect_args={
            "connect_timeout": int(os.getenv("FNBR_DB_CONNECT_TIMEOUT", "10")),
            "read_timeout": int(os.getenv("FNBR_DB_QUERY_TIMEOUT", "30")),
            "write_timeout": int(os.getenv("FNBR_DB_QUERY_TIMEOUT", "30")),
        },
    )

    if engine.dialect.name in {"mysql", "mariadb"}:
        @event.listens_for(engine, "connect")
        def make_connection_read_only(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("SET SESSION TRANSACTION READ ONLY")
            finally:
                cursor.close()
    return engine


def build_pipeline(predictor_mode: str = "model") -> AnalysisPipeline:
    database_url = os.environ["FNBR_DATABASE_URL"]
    revision = os.environ["FNBR_LEXICON_REVISION"]
    engine = create_read_only_engine(database_url)
    repository = MariaDBLexiconRepository(engine, revision=revision)

    # Imported lazily so lightweight conversion and contract tests do not load torch.
    from trankit import Pipeline

    cache_dir = os.getenv("TRANKIT_CACHE_DIR", "./cache/trankit")
    embedding = os.getenv("TRANKIT_EMBEDDING", "xlm-roberta-large")
    gpu = os.getenv("TRANKIT_GPU", "false").casefold() == "true"
    standard = Pipeline(
        lang="portuguese", cache_dir=cache_dir, gpu=gpu, embedding=embedding
    )
    type_predictor: LemmaTypePredictor
    if predictor_mode == "lexical":
        type_predictor = LexicalPriorPredictor()
    elif predictor_mode == "model":
        fnbr_language = os.getenv("FNBR_TRANKIT_LANGUAGE", "customized")
        fnbr_cache = os.getenv("FNBR_TRANKIT_CACHE_DIR", "./cache/fnbr")
        fnbr = Pipeline(
            lang=fnbr_language, cache_dir=fnbr_cache, gpu=gpu, embedding=embedding
        )
        type_predictor = TrankitLemmaTypePredictor(
            fnbr, model_version=os.getenv("FNBR_MODEL_VERSION", "unversioned")
        )
    else:
        raise ValueError("predictor_mode must be 'lexical' or 'model'")

    return AnalysisPipeline(
        parser=TrankitUDParser(
            standard,
            model_version="trankit-1.1.2@{}".format(UPSTREAM_TRANKIT_REVISION[:12]),
        ),
        lexical_processor=LexicalProcessor(repository),
        type_predictor=type_predictor,
        database_schema_version=repository.schema_version,
    )


class LazyConfiguredPipeline:
    """Thread-safe deployment wrapper; configuration is resolved on first use."""

    def __init__(self) -> None:
        self._pipeline: Optional[AnalysisPipeline] = None
        self._lock = threading.Lock()

    def initialize(self) -> None:
        if self._pipeline is None:
            with self._lock:
                if self._pipeline is None:
                    try:
                        self._pipeline = build_pipeline(
                            predictor_mode=os.getenv("FNBR_PREDICTOR_MODE", "model")
                        )
                    except SQLAlchemyError as error:
                        raise ConnectionError("FNBr database is unavailable") from error

    def analyze(self, text: str, top_k: int = 3) -> Dict[str, Any]:
        self.initialize()
        assert self._pipeline is not None
        return self._pipeline.analyze(text, top_k)
