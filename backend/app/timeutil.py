from datetime import datetime, timezone


def utcnow() -> datetime:
    """Naive UTC timestamp (stored as-is in DateTime columns)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
