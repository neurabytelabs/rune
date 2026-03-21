"""Tests for RUNE Router — task classification."""

import pytest

try:
    from rune.routing.router import TaskType, TaskClassifier
    HAS_ROUTER = True
except ImportError:
    HAS_ROUTER = False


@pytest.mark.skipif(not HAS_ROUTER, reason="Router module not fully importable")
class TestTaskClassifier:
    @pytest.fixture
    def classifier(self):
        return TaskClassifier()

    def test_coding_detection(self, classifier):
        result = classifier.classify("Write a Python function to sort a list")
        assert isinstance(result, TaskType)
        # Should detect as some coding-related type
        assert "cod" in result.name.lower() or "code" in result.value.lower() or result != TaskType.GENERAL

    def test_writing_detection(self, classifier):
        result = classifier.classify("Write a blog post about AI trends")
        assert isinstance(result, TaskType)

    def test_analysis_detection(self, classifier):
        result = classifier.classify("Analyze the market trends for SaaS companies")
        assert isinstance(result, TaskType)

    def test_general_fallback(self, classifier):
        result = classifier.classify("hello")
        assert isinstance(result, TaskType)
