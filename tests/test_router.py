"""Tests for intent router — keyword heuristics with clean interface."""

import pytest
from src.agents.router import classify_intent, IntentResult


class TestClassifyWhat:
    @pytest.mark.parametrize("q", [
        "What were GlucoJoy's monthly primary sales vs target in North in Nov 2025?",
        "How many units of SparkClean were sold in Mumbai?",
        "Show me the sales data for last week",
        "What is the total revenue for Q4?",
        "List all SKUs in the Detergent category",
        "Give me the sales volume for CrispKing",
        "What are the monthly targets for ChaiRaja?",
    ])
    def test_what_questions(self, q):
        result = classify_intent(q)
        assert result.intent == "WHAT"
        assert result.confidence >= 0.5

    def test_what_question_high_confidence(self):
        result = classify_intent("What were the sales figures for last month?")
        assert result.intent == "WHAT"
        assert result.confidence >= 0.6


class TestClassifyWhy:
    @pytest.mark.parametrize("q", [
        "Why did SparkClean 1kg primary sales spike in Mumbai in week of 16 Sep 2025?",
        "What caused the dip in GlucoJoy sales?",
        "Why is there a stockout in Delhi?",
        "What led to the sales decline in Bengaluru?",
        "Reason for the promotion discount increase?",
    ])
    def test_why_questions(self, q):
        result = classify_intent(q)
        assert result.intent == "WHY"
        assert result.confidence >= 0.5

    def test_why_question_high_confidence(self):
        result = classify_intent("Why did sales drop in the North region?")
        assert result.intent == "WHY"
        assert result.confidence >= 0.6


class TestClassifyWhatToDo:
    @pytest.mark.parametrize("q", [
        "What should we do about the stockout in Chennai?",
        "Recommend actions to improve SparkClean sales",
        "How to improve distributor performance in the West?",
        "Suggest next steps for the GlucoJoy launch",
        "What can we do to reduce stockouts?",
    ])
    def test_what_to_do_questions(self, q):
        result = classify_intent(q)
        assert result.intent == "WHAT_TO_DO"
        assert result.confidence >= 0.5

    def test_what_to_do_high_confidence(self):
        result = classify_intent("What should we do to increase sales?")
        assert result.intent == "WHAT_TO_DO"
        assert result.confidence >= 0.6


class TestClassifyOutOfDomain:
    @pytest.mark.parametrize("q", [
        "What is the weather today?",
        "Who won the cricket match?",
        "Tell me a joke",
        "What is the capital of France?",
        "How do I bake a cake?",
    ])
    def test_out_of_domain_questions(self, q):
        result = classify_intent(q)
        assert result.intent == "OUT_OF_DOMAIN"

    def test_out_of_domain_high_confidence(self):
        result = classify_intent("What is the meaning of life?")
        assert result.intent == "OUT_OF_DOMAIN"
        assert result.confidence >= 0.6


class TestClassifierInterface:
    def test_returns_intent_result(self):
        result = classify_intent("What were the sales?")
        assert isinstance(result, IntentResult)

    def test_intent_result_has_intent(self):
        result = classify_intent("What were the sales?")
        assert hasattr(result, "intent")

    def test_intent_result_has_confidence(self):
        result = classify_intent("What were the sales?")
        assert hasattr(result, "confidence")

    def test_confidence_is_float(self):
        result = classify_intent("What were the sales?")
        assert isinstance(result.confidence, float)

    def test_confidence_in_range(self):
        result = classify_intent("What were the sales?")
        assert 0.0 <= result.confidence <= 1.0

    def test_intent_is_valid_enum(self):
        result = classify_intent("What were the sales?")
        assert result.intent in {"WHAT", "WHY", "WHAT_TO_DO", "OUT_OF_DOMAIN"}

    def test_empty_string_returns_out_of_domain(self):
        result = classify_intent("")
        assert result.intent == "OUT_OF_DOMAIN"

    def test_short_gibberish_returns_out_of_domain(self):
        result = classify_intent("abc xyz")
        assert result.intent == "OUT_OF_DOMAIN"


class TestEdgeCases:
    def test_sales_keyword_favors_what_over_out_of_domain(self):
        result = classify_intent("What is the sales target for next month?")
        assert result.intent == "WHAT"

    def test_because_clause_does_not_override_why(self):
        result = classify_intent("Why did sales drop because of the promo?")
        assert result.intent == "WHY"

    def test_recommend_triggers_what_to_do(self):
        result = classify_intent("I recommend increasing the discount")
        assert result.intent in ("WHAT_TO_DO", "WHAT")

    def test_question_with_multiple_intent_signals(self):
        result = classify_intent("What caused the spike and what should we do?")
        assert result.intent in ("WHY", "WHAT_TO_DO")