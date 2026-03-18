"""
src/utils.py
~~~~~~~~~~~~
Shared utility functions used across all demo notebooks.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any


# ──────────────────────────────────────────────────────────────────────────────
# String / text helpers
# ──────────────────────────────────────────────────────────────────────────────

def normalise_sentiment(raw: str) -> str:
    """Map a raw LLM response to one of the three canonical sentiment labels.

    Parameters
    ----------
    raw:
        The raw text returned by the LLM (case-insensitive).

    Returns
    -------
    str
        One of ``"positive"``, ``"negative"``, or ``"neutral"``.

    Examples
    --------
    >>> normalise_sentiment("POSITIVE")
    'positive'
    >>> normalise_sentiment("  Negative. ")
    'negative'
    >>> normalise_sentiment("I cannot say")
    'neutral'
    """
    cleaned = raw.strip().lower()
    if "positive" in cleaned:
        return "positive"
    if "negative" in cleaned:
        return "negative"
    return "neutral"


def truncate_text(text: str, max_chars: int = 512) -> str:
    """Truncate *text* to at most *max_chars* characters, adding an ellipsis.

    Parameters
    ----------
    text:
        Input string.
    max_chars:
        Maximum number of characters to retain (default 512).

    Returns
    -------
    str
        Possibly truncated string.

    Examples
    --------
    >>> truncate_text("hello world", 5)
    'hello…'
    >>> truncate_text("short", 100)
    'short'
    """
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\u2026"


def slugify(text: str) -> str:
    """Convert *text* into a lower-case alphanumeric slug suitable for IDs.

    Examples
    --------
    >>> slugify("My Experiment #1!")
    'my_experiment_1'
    """
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s-]+", "_", text)
    return text


# ──────────────────────────────────────────────────────────────────────────────
# Date / time helpers
# ──────────────────────────────────────────────────────────────────────────────

def days_between(start: datetime, end: datetime) -> int:
    """Return the number of whole days between two datetime objects.

    Parameters
    ----------
    start, end:
        Datetime objects (timezone-naive or both timezone-aware).

    Returns
    -------
    int
        ``(end - start).days`` — may be negative if *end* < *start*.

    Examples
    --------
    >>> from datetime import datetime
    >>> days_between(datetime(2024, 1, 1), datetime(2024, 1, 11))
    10
    """
    return (end - start).days


def clamp_date(dt: datetime, earliest: datetime, latest: datetime) -> datetime:
    """Clamp *dt* to the inclusive range [*earliest*, *latest*].

    Examples
    --------
    >>> from datetime import datetime
    >>> clamp_date(datetime(2020, 1, 1), datetime(2022, 1, 1), datetime(2024, 1, 1))
    datetime.datetime(2022, 1, 1, 0, 0)
    """
    if dt < earliest:
        return earliest
    if dt > latest:
        return latest
    return dt


# ──────────────────────────────────────────────────────────────────────────────
# Feature engineering helpers
# ──────────────────────────────────────────────────────────────────────────────

def compute_sentiment_score(
    positive: int,
    negative: int,
    neutral: int,
) -> float:
    """Compute a normalised sentiment score in [-1, +1].

    Formula: ``(positive - negative) / (positive + negative + neutral + 1)``

    The ``+1`` denominator smooths zero-review customers.

    Parameters
    ----------
    positive, negative, neutral:
        Counts of LLM-classified reviews per sentiment class.

    Returns
    -------
    float
        Score in [-1, +1]; higher is more positive.

    Examples
    --------
    >>> compute_sentiment_score(8, 2, 0)
    0.6
    >>> compute_sentiment_score(0, 0, 0)
    0.0
    """
    denom = positive + negative + neutral + 1
    return (positive - negative) / denom


def compute_support_intensity(num_cases: int, tenure_days: int) -> float:
    """Cases per month, normalised by tenure.

    Parameters
    ----------
    num_cases:
        Total number of support cases raised.
    tenure_days:
        Customer tenure in days (must be > 0 to avoid division by zero).

    Returns
    -------
    float
        Monthly support-case rate; 0.0 when *tenure_days* <= 0.

    Examples
    --------
    >>> compute_support_intensity(6, 60)
    3.0
    >>> compute_support_intensity(5, 0)
    0.0
    """
    if tenure_days <= 0:
        return 0.0
    return num_cases / tenure_days * 30


# ──────────────────────────────────────────────────────────────────────────────
# Config helpers
# ──────────────────────────────────────────────────────────────────────────────

def deep_get(mapping: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Safely traverse a nested dictionary.

    Parameters
    ----------
    mapping:
        The dictionary to traverse.
    *keys:
        A sequence of keys representing the path.
    default:
        Value returned when a key is missing (default ``None``).

    Returns
    -------
    Any
        The value at the path, or *default*.

    Examples
    --------
    >>> deep_get({"a": {"b": 42}}, "a", "b")
    42
    >>> deep_get({"a": {}}, "a", "c", default=-1)
    -1
    """
    current = mapping
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current
