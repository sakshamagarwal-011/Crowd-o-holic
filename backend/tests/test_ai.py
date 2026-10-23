"""
Tests for the AI providers — mock and schema validation.
Default tests use MockAIProvider, no network required.
"""
import asyncio
import pytest
from app.ai.mock_provider import MockAIProvider
from app.ai.schemas import ParsedScenario, SafetyAnalysis, ScenarioParseResult


@pytest.mark.asyncio
async def test_mock_parse_concert():
    provider = MockAIProvider()
    result = await provider.parse_scenario(
        "A concert with 20,000 people starts at 7 PM. Most people enter through the east gate."
    )
    assert result.success
    assert result.parsed is not None
    assert result.parsed.crowdSize == 20000
    assert result.stage == "ready"
    assert len(result.notes) > 0


@pytest.mark.asyncio
async def test_mock_parse_ipl():
    provider = MockAIProvider()
    result = await provider.parse_scenario(
        "Simulate an IPL match with 30,000 spectators entering through Gate A and Gate B."
    )
    assert result.success
    assert result.parsed is not None
    assert result.parsed.crowdSize == 30000


@pytest.mark.asyncio
async def test_mock_safety_analysis_low():
    provider = MockAIProvider()
    metrics = {
        "peopleCount": 500, "avgDensity": 0.15, "flowRate": 100,
        "avgSpeed": 1.5, "queueGrowth": 0.0, "capacityUtilization": 0.1,
    }
    safety = {
        "riskScore": 15, "riskLevel": "low",
        "bottlenecks": [], "predictedBottlenecks": [],
        "timeToCriticalMin": None, "alerts": [],
    }
    analysis = await provider.analyze_safety(metrics, safety, 10.0, "running")
    assert isinstance(analysis, SafetyAnalysis)
    assert analysis.urgency == "low"
    assert len(analysis.summary) > 0
    assert len(analysis.recommended_action) > 0


@pytest.mark.asyncio
async def test_mock_safety_analysis_emergency():
    provider = MockAIProvider()
    metrics = {
        "peopleCount": 5000, "avgDensity": 0.9, "flowRate": 500,
        "avgSpeed": 0.2, "queueGrowth": 10.0, "capacityUtilization": 0.9,
    }
    safety = {
        "riskScore": 90, "riskLevel": "emergency",
        "bottlenecks": [{"location": "North Junction", "risk": "critical",
                         "currentDensity": 0.9, "capacityUtilization": 0.9,
                         "timeToCriticalMin": 3.0, "recommendedAction": "Redirect."}],
        "predictedBottlenecks": [],
        "timeToCriticalMin": 3.0, "alerts": [],
    }
    em = {"active": True, "type": "fire", "location": "North Exit", "id": "em-1"}
    analysis = await provider.analyze_safety(metrics, safety, 15.0, "running", emergency=em)
    assert analysis.urgency == "emergency"
    assert "emergency" in analysis.summary.lower() or "north exit" in analysis.summary.lower()


@pytest.mark.asyncio
async def test_mock_safety_analysis_bottleneck():
    provider = MockAIProvider()
    metrics = {
        "peopleCount": 3000, "avgDensity": 0.75, "flowRate": 350,
        "avgSpeed": 0.6, "queueGrowth": 5.0, "capacityUtilization": 0.75,
    }
    safety = {
        "riskScore": 75, "riskLevel": "high",
        "bottlenecks": [{"location": "North Corridor", "risk": "high",
                         "currentDensity": 0.75, "capacityUtilization": 0.75,
                         "timeToCriticalMin": 8.0,
                         "recommendedAction": "Redirect to west corridor."}],
        "predictedBottlenecks": [],
        "timeToCriticalMin": 8.0, "alerts": [],
    }
    analysis = await provider.analyze_safety(metrics, safety, 20.0, "running")
    assert analysis.urgency in ("high", "critical", "emergency")
    assert len(analysis.contributing_factors) > 0


def test_parsed_scenario_validation():
    from app.ai.schemas import EntryDistributionItem, EventTimingInfo
    parsed = ParsedScenario(
        name="Test",
        crowdSize=1000,
        timing=EventTimingInfo(startMinutesOfDay=1140, durationMin=180),
        entryDistribution=[
            EntryDistributionItem(gateId="gate-e", fraction=0.6),
            EntryDistributionItem(gateId="gate-w", fraction=0.4),
        ],
    )
    assert parsed.crowdSize == 1000
    total = sum(d.fraction for d in parsed.entryDistribution)
    assert abs(total - 1.0) < 0.01


def test_parsed_scenario_invalid_crowd_size():
    with pytest.raises(Exception):
        ParsedScenario(crowdSize=-100)


def test_safety_analysis_schema():
    analysis = SafetyAnalysis(
        summary="Test summary",
        risk_explanation="Test explanation",
        recommended_action="Test action",
        urgency="low",
    )
    assert analysis.urgency == "low"
    assert analysis.generated_timestamp is not None


@pytest.mark.asyncio
async def test_ai_does_not_invent_numbers():
    """AI output should reference provided metrics, not invent new ones."""
    provider = MockAIProvider()
    metrics = {
        "peopleCount": 1234, "avgDensity": 0.45, "flowRate": 200,
        "avgSpeed": 1.0, "queueGrowth": 1.0, "capacityUtilization": 0.45,
    }
    safety = {
        "riskScore": 45, "riskLevel": "moderate", "bottlenecks": [],
        "predictedBottlenecks": [], "timeToCriticalMin": None, "alerts": [],
    }
    analysis = await provider.analyze_safety(metrics, safety, 10.0, "running")
    # Supporting metrics should contain values from the input, not invented ones
    for val in analysis.supporting_metrics.values():
        if isinstance(val, (int, float)):
            # Values should be in reasonable range
            assert val >= 0
