"""
tests/test_utils.py
~~~~~~~~~~~~~~~~~~~
Unit tests for src/utils.py
"""

import sys
import os
from datetime import datetime

# Allow importing src/utils without installing the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.utils import (
    normalise_sentiment,
    truncate_text,
    slugify,
    days_between,
    clamp_date,
    compute_sentiment_score,
    compute_support_intensity,
    deep_get,
)


# ──────────────────────────────────────────────────────────────────────────────
# normalise_sentiment
# ──────────────────────────────────────────────────────────────────────────────

class TestNormaliseSentiment:
    def test_positive_lower(self):
        assert normalise_sentiment("positive") == "positive"

    def test_positive_upper(self):
        assert normalise_sentiment("POSITIVE") == "positive"

    def test_positive_with_whitespace(self):
        assert normalise_sentiment("  Positive  ") == "positive"

    def test_negative_mixed_case(self):
        assert normalise_sentiment("Negative.") == "negative"

    def test_neutral_default(self):
        assert normalise_sentiment("I have no idea") == "neutral"

    def test_neutral_explicit(self):
        assert normalise_sentiment("neutral") == "neutral"

    def test_empty_string_returns_neutral(self):
        assert normalise_sentiment("") == "neutral"

    def test_priority_positive_over_neutral(self):
        # "positive" substring wins
        assert normalise_sentiment("not negative but positive") == "positive"


# ──────────────────────────────────────────────────────────────────────────────
# truncate_text
# ──────────────────────────────────────────────────────────────────────────────

class TestTruncateText:
    def test_short_string_unchanged(self):
        assert truncate_text("hi", 100) == "hi"

    def test_exact_length_unchanged(self):
        assert truncate_text("hello", 5) == "hello"

    def test_truncation_adds_ellipsis(self):
        result = truncate_text("hello world", 5)
        assert result == "hello\u2026"
        assert len(result) == 6

    def test_default_max_chars(self):
        long_text = "a" * 600
        result = truncate_text(long_text)
        assert len(result) == 513  # 512 chars + ellipsis

    def test_unicode_input(self):
        result = truncate_text("héllo", 3)
        assert result == "hél\u2026"


# ──────────────────────────────────────────────────────────────────────────────
# slugify
# ──────────────────────────────────────────────────────────────────────────────

class TestSlugify:
    def test_basic(self):
        assert slugify("Hello World") == "hello_world"

    def test_special_chars_removed(self):
        assert slugify("My Experiment #1!") == "my_experiment_1"

    def test_hyphens_become_underscores(self):
        assert slugify("foo-bar") == "foo_bar"

    def test_multiple_spaces_collapsed(self):
        assert slugify("foo   bar") == "foo_bar"

    def test_already_slug(self):
        assert slugify("already_slug") == "already_slug"

    def test_empty_string(self):
        assert slugify("") == ""


# ──────────────────────────────────────────────────────────────────────────────
# days_between
# ──────────────────────────────────────────────────────────────────────────────

class TestDaysBetween:
    def test_positive_difference(self):
        assert days_between(datetime(2024, 1, 1), datetime(2024, 1, 11)) == 10

    def test_zero_difference(self):
        d = datetime(2024, 6, 1)
        assert days_between(d, d) == 0

    def test_negative_difference(self):
        assert days_between(datetime(2024, 1, 11), datetime(2024, 1, 1)) == -10


# ──────────────────────────────────────────────────────────────────────────────
# clamp_date
# ──────────────────────────────────────────────────────────────────────────────

class TestClampDate:
    EARLIEST = datetime(2022, 1, 1)
    LATEST   = datetime(2024, 12, 31)

    def test_within_range_unchanged(self):
        dt = datetime(2023, 6, 15)
        assert clamp_date(dt, self.EARLIEST, self.LATEST) == dt

    def test_below_earliest_clamped(self):
        dt = datetime(2020, 1, 1)
        assert clamp_date(dt, self.EARLIEST, self.LATEST) == self.EARLIEST

    def test_above_latest_clamped(self):
        dt = datetime(2025, 6, 1)
        assert clamp_date(dt, self.EARLIEST, self.LATEST) == self.LATEST

    def test_equal_to_earliest_unchanged(self):
        assert clamp_date(self.EARLIEST, self.EARLIEST, self.LATEST) == self.EARLIEST

    def test_equal_to_latest_unchanged(self):
        assert clamp_date(self.LATEST, self.EARLIEST, self.LATEST) == self.LATEST


# ──────────────────────────────────────────────────────────────────────────────
# compute_sentiment_score
# ──────────────────────────────────────────────────────────────────────────────

class TestComputeSentimentScore:
    def test_all_positive(self):
        # (10 - 0) / (10 + 0 + 0 + 1) = 10/11
        assert abs(compute_sentiment_score(10, 0, 0) - 10 / 11) < 1e-9

    def test_all_negative(self):
        assert abs(compute_sentiment_score(0, 10, 0) - (-10 / 11)) < 1e-9

    def test_zero_reviews(self):
        assert compute_sentiment_score(0, 0, 0) == 0.0

    def test_known_values(self):
        # (8 - 2) / (8 + 2 + 0 + 1) = 6/11
        assert abs(compute_sentiment_score(8, 2, 0) - 6 / 11) < 1e-9

    def test_score_in_range(self):
        score = compute_sentiment_score(3, 7, 5)
        assert -1.0 <= score <= 1.0


# ──────────────────────────────────────────────────────────────────────────────
# compute_support_intensity
# ──────────────────────────────────────────────────────────────────────────────

class TestComputeSupportIntensity:
    def test_basic(self):
        # 6 cases in 60 days → 6/60*30 = 3.0
        assert compute_support_intensity(6, 60) == 3.0

    def test_zero_tenure_returns_zero(self):
        assert compute_support_intensity(5, 0) == 0.0

    def test_negative_tenure_returns_zero(self):
        assert compute_support_intensity(5, -10) == 0.0

    def test_zero_cases(self):
        assert compute_support_intensity(0, 30) == 0.0


# ──────────────────────────────────────────────────────────────────────────────
# deep_get
# ──────────────────────────────────────────────────────────────────────────────

class TestDeepGet:
    def test_existing_path(self):
        assert deep_get({"a": {"b": 42}}, "a", "b") == 42

    def test_missing_key_returns_default(self):
        assert deep_get({"a": {}}, "a", "c", default=-1) == -1

    def test_default_is_none_when_not_specified(self):
        assert deep_get({}, "x") is None

    def test_top_level_key(self):
        assert deep_get({"foo": "bar"}, "foo") == "bar"

    def test_nested_three_levels(self):
        d = {"x": {"y": {"z": "found"}}}
        assert deep_get(d, "x", "y", "z") == "found"

    def test_non_dict_in_path_returns_default(self):
        d = {"a": "string_not_dict"}
        assert deep_get(d, "a", "b", default="fallback") == "fallback"
