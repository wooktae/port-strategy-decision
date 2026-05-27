import os


def get_db_config():
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
