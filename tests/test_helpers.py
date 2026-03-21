"""Tests for CLI helpers — intent detection, config."""

import pytest
from rune.cli.helpers import detect_intent


class TestDetectIntent:
    def test_coding_detection(self):
        result = detect_intent("debug this Python function")
        assert result["domain"] == "CODING"
        assert result["lang"] == "en"

    def test_writing_detection(self):
        result = detect_intent("write a blog post about AI")
        assert result["domain"] == "WRITING"
        assert result["lang"] == "en"

    def test_analysis_detection(self):
        result = detect_intent("analyze the competitor landscape")
        assert result["domain"] == "ANALYSIS"
        assert result["lang"] == "en"

    def test_creative_detection(self):
        result = detect_intent("design a logo for my startup")
        assert result["domain"] == "CREATIVE"
        assert result["lang"] == "en"

    def test_research_detection(self):
        result = detect_intent("research quantum computing advances")
        assert result["domain"] == "RESEARCH"
        assert result["lang"] == "en"

    def test_turkish_detection_by_chars(self):
        result = detect_intent("şu fonksiyonu debug et")
        assert result["lang"] == "tr"

    def test_turkish_detection_by_words(self):
        result = detect_intent("blog yazisi yaz hakkinda AI")
        assert result["lang"] == "tr"

    def test_general_fallback(self):
        result = detect_intent("hello there")
        assert result["domain"] == "GENERAL"

    def test_prompt_preserved(self):
        text = "some prompt text"
        result = detect_intent(text)
        assert result["prompt"] == text
