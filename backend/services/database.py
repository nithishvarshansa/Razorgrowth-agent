from pathlib import Path

from ..config import get_settings


def ensure_database_directory() -> None:
    """Prepare the local SQLite directory without creating a schema yet."""
    database_url = get_settings().database_url
    prefix = "sqlite:///./"
    if database_url.startswith(prefix):
        database_path = Path(database_url.removeprefix(prefix))
        database_path.parent.mkdir(parents=True, exist_ok=True)
