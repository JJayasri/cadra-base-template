"""Tests for WHAT agent — aggregation engine for WHAT queries."""

import pandas as pd
import pytest

from src.agents.what_agent import WhatAgent, WhatQuery, WhatResult


@pytest.fixture
def agent():
    from src.data.loader import load_all_csvs
    from src.data.cleaner import clean_all
    raw = load_all_csvs()
    cleaned = clean_all(raw)
    return WhatAgent(cleaned)


class TestWhatQueryParsing:
    def test_parse_glucojoy_north_nov2025(self, agent):
        q = agent.parse("What were GlucoJoy's monthly primary sales vs target in the North region in November 2025?")
        assert q is not None
        assert q.brand == "GlucoJoy"
        assert "North" in q.regions
        assert q.month == 11
        assert q.year == 2025
        assert q.time_grain == "monthly"
        assert q.compare_target is True

    def test_parse_sparkclean_1kg_mumbai_sep2025(self, agent):
        q = agent.parse("What were SparkClean 1kg primary sales in Mumbai in September 2025?")
        assert q is not None
        assert q.brand == "SparkClean"
        assert "Mumbai" in q.territories
        assert "1kg" in q.pack_size or "1 kg" in q.pack_size
        assert q.month == 9
        assert q.year == 2025
        assert q.compare_target is False

    def test_parse_what_question_without_region(self, agent):
        q = agent.parse("What was the total sales in July 2025?")
        assert q is not None
        assert q.month == 7
        assert q.year == 2025

    def test_parse_weekly_question(self, agent):
        q = agent.parse("What were the sales for the week of 16 Sep 2025?")
        assert q is not None
        assert q.time_grain == "weekly"

    def test_parse_how_many_units(self, agent):
        q = agent.parse("How many units of CrispKing were sold in Delhi?")
        assert q is not None
        assert q.brand == "CrispKing"

    def test_parse_question_without_entity(self, agent):
        q = agent.parse("What were the sales?")
        assert q is not None

    def test_parse_non_what_returns_query(self, agent):
        q = agent.parse("Tell me a joke")
        assert q is not None
        assert q.metric == "sales"


class TestWhatQueryExecution:
    def test_glucojoy_north_nov2025_sales(self, agent):
        q = agent.parse("What were GlucoJoy's monthly primary sales vs target in the North region in November 2025?")
        result = agent.execute(q)
        assert result is not None
        assert result.sales_value == 861938.25
        assert result.target_value == 1026116.06
        assert result.metric == "sales_vs_target"
        assert result.currency == "INR"

    def test_sparkclean_1kg_mumbai_sep2025_sales(self, agent):
        q = agent.parse("What were SparkClean 1kg primary sales in Mumbai in September 2025?")
        result = agent.execute(q)
        assert result is not None
        assert result.sales_value == 176779.0
        assert result.sales_units == 2773.0
        assert result.metric == "sales"

    def test_how_many_units_query(self, agent):
        q = agent.parse("How many units of CrispKing were sold?")
        result = agent.execute(q)
        assert result is not None
        assert result.sales_units is not None
        assert result.sales_units > 0

    def test_execute_returns_sales_value(self, agent):
        q = agent.parse("What were the sales in July 2025?")
        result = agent.execute(q)
        assert result is not None
        assert result.sales_value > 0

    def test_execute_returns_empty_result_for_bogus(self, agent):
        q = WhatQuery(metric="sales", territories=["Nowhere"], month=1, year=2025)
        result = agent.execute(q)
        assert result is None


class TestWhatAgentFormatResponse:
    def test_format_response_has_correct_schema(self, agent):
        q = agent.parse("What were GlucoJoy's monthly primary sales vs target in the North region in November 2025?")
        result = agent.execute(q)
        response = agent.format_response(q, result)
        assert "answer" in response
        assert "intent" in response
        assert "citations" in response
        assert "confidence" in response
        assert "status" in response
        assert response["intent"] == "WHAT"
        assert response["status"] == "OK"

    def test_format_response_includes_sales_value(self, agent):
        q = agent.parse("What were GlucoJoy's monthly primary sales vs target in the North region in November 2025?")
        result = agent.execute(q)
        response = agent.format_response(q, result)
        assert "861,938" in response["answer"]
        assert response["confidence"] >= 0.7

    def test_format_response_includes_target_comparison(self, agent):
        q = agent.parse("What were GlucoJoy's monthly primary sales vs target in the North region in November 2025?")
        result = agent.execute(q)
        response = agent.format_response(q, result)
        assert "target" in response["answer"].lower()
        assert "1,026,116" in response["answer"]

    def test_format_response_has_citations(self, agent):
        q = agent.parse("What were GlucoJoy's monthly primary sales vs target in the North region in November 2025?")
        result = agent.execute(q)
        response = agent.format_response(q, result)
        assert len(response["citations"]) > 0
        assert "fact_primary_sales" in response["citations"]
        assert "fact_targets" in response["citations"]

    def test_format_response_none_result(self, agent):
        q = WhatQuery(metric="sales", territories=["Nowhere"], month=1, year=2025)
        response = agent.format_response(q, None)
        assert "Unable to answer" in response["answer"]
        assert response["status"] == "ABSTAINED"


class TestWhatAgentIntegration:
    def test_agent_handles_brand_mapping(self, agent):
        result = agent.execute(agent.parse("What were the sales for GlucoJoy?"))
        assert result is not None
        assert result.sales_value > 0

    def test_agent_handles_region_mapping(self, agent):
        result = agent.execute(agent.parse("What were the sales in the North region?"))
        assert result is not None
        assert result.sales_value > 0

    def test_agent_handles_territory_mapping_mumbai(self, agent):
        result = agent.execute(agent.parse("What were the sales in Mumbai?"))
        assert result is not None
        assert result.sales_value > 0

    def test_agent_handles_category_filter(self, agent):
        result = agent.execute(agent.parse("What were the sales for Detergent?"))
        assert result is not None
        assert result.sales_value > 0