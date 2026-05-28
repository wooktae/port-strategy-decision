"""decision 모듈의 PostgreSQL 접속 설정을 제공한다.

DB 접속값은 `INTEREST_DB_*` 환경변수에서 읽고, password 기본값은 두지 않는다.
민감정보 값은 코드와 문서에 기록하지 않으며 search_path는 domain schema 순서를 따른다.
"""

import os


def get_db_config():
    """psycopg2.connect에 전달할 DB 설정 dict를 환경변수 기반으로 만든다."""
    password = os.environ.get("INTEREST_DB_PASSWORD")
    if not password:
        raise RuntimeError("INTEREST_DB_PASSWORD environment variable is required")

    return {
        "host": os.environ.get("INTEREST_DB_HOST") or "localhost",
        "port": int(os.environ.get("INTEREST_DB_PORT") or "5433"),
        "dbname": os.environ.get("INTEREST_DB_NAME") or "portfolio",
        "user": os.environ.get("INTEREST_DB_USER") or "postgres",
        "password": password,
        "options": "-c search_path=decision,research,preprocessor,execution,connector,reference,legacy,public",
    }
