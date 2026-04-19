def _savings(raw: str, filtered: str) -> float:
    """Return % character reduction. Used across all test modules."""
    if not raw:
        return 0.0
    return (1 - len(filtered) / len(raw)) * 100
