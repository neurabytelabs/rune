"""Tests for SpinozaValidator — local heuristic validation."""

import pytest
from rune.core.validator import SpinozaValidator, ValidationReport


@pytest.fixture
def validator():
    return SpinozaValidator()


GOOD_TEXT = """
# How to Deploy a Production Application

## Step 1: Prepare the Environment
Install the required dependencies because they ensure compatibility.

## Step 2: Configure the Database
Set up PostgreSQL with the following connection string. Therefore, your app
will have persistent storage.

## Step 3: Deploy
Run the deployment script:
```bash
./deploy.sh --env production
```

## Step 4: Verify
Check the health endpoint to ensure everything is running correctly.
Furthermore, monitor the logs for any errors.

This approach is effective and powerful for production deployments.
"""

SHORT_TEXT = "Hello world"

AI_SLOP_TEXT = """
As an AI language model, I'd be happy to help you with that! Great question!
Certainly! Let me help you understand this topic. In today's rapidly evolving
landscape, it's worth noting that there are many aspects to consider.
Here's a comprehensive overview of the situation.
"""


class TestSpinozaValidator:
    def test_validate_returns_report(self, validator):
        report = validator.validate(GOOD_TEXT)
        assert isinstance(report, ValidationReport)
        assert 0.0 <= report.overall <= 1.0
        assert report.grade in ("A", "A-", "B+", "B", "B-", "C+", "C", "D", "F")
        assert len(report.scores) == 4
        assert "conatus" in report.scores
        assert "ratio" in report.scores
        assert "laetitia" in report.scores
        assert "natura" in report.scores

    def test_good_text_scores_well(self, validator):
        report = validator.validate(GOOD_TEXT)
        assert report.overall >= 0.60, f"Good text should score >= 0.60, got {report.overall}"
        assert report.grade in ("A", "A-", "B+", "B", "B-", "C+", "C")

    def test_empty_text_scores_zero(self, validator):
        report = validator.validate("")
        assert report.overall == 0.0
        assert report.grade == "F"

    def test_whitespace_text_scores_zero(self, validator):
        report = validator.validate("   \n\n  ")
        assert report.overall == 0.0
        assert report.grade == "F"

    def test_short_text_scores_low(self, validator):
        report = validator.validate(SHORT_TEXT)
        assert report.overall < 0.65, f"Short text should score < 0.65, got {report.overall}"

    def test_ai_slop_penalized(self, validator):
        good_report = validator.validate(GOOD_TEXT)
        slop_report = validator.validate(AI_SLOP_TEXT)
        # AI slop should score lower on natura
        assert slop_report.scores["natura"].score < good_report.scores["natura"].score

    def test_grade_boundaries(self, validator):
        from rune.core.validator import _grade
        assert _grade(0.95) == "A"
        assert _grade(0.90) == "A"
        assert _grade(0.87) == "A-"
        assert _grade(0.82) == "B+"
        assert _grade(0.76) == "B"
        assert _grade(0.71) == "B-"
        assert _grade(0.66) == "C+"
        assert _grade(0.61) == "C"
        assert _grade(0.55) == "D"
        assert _grade(0.40) == "F"
        assert _grade(0.0) == "F"

    def test_format_report(self, validator):
        report = validator.validate(GOOD_TEXT)
        formatted = validator.format_report(report)
        assert "Spinoza Validation Report" in formatted
        assert "conatus" in formatted
        assert "ratio" in formatted
        assert "Overall" in formatted
        assert report.grade in formatted

    def test_word_and_char_count(self, validator):
        report = validator.validate(GOOD_TEXT)
        assert report.word_count > 0
        assert report.char_count > 0
        assert report.char_count == len(GOOD_TEXT)

    def test_pillar_weights_sum_to_one(self, validator):
        report = validator.validate(GOOD_TEXT)
        total_weight = sum(p.weight for p in report.scores.values())
        assert abs(total_weight - 1.0) < 0.001
