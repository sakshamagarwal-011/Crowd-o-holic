import pytest

from app.ai.openrouter_provider import OpenRouterAIProvider


@pytest.mark.asyncio
async def test_openrouter_scenario_response_is_validated(monkeypatch):
    provider = OpenRouterAIProvider()

    async def fake_complete(*_args, **_kwargs):
        return '''{
          "name": "Rainy concert",
          "crowdSize": 18000,
          "timing": {"startMinutesOfDay": 1140, "durationMin": 180, "arrivalPattern": "surge", "departurePattern": "surge"},
          "entryDistribution": [{"gateId": "gate-e", "fraction": 0.7}, {"gateId": "gate-w", "fraction": 0.3}],
          "crowdGroups": [], "entryRate": 600, "exitRate": 800,
          "notes": ["Rain contingency requested"]
        }'''

    monkeypatch.setattr(provider, "_complete", fake_complete)
    result = await provider.parse_scenario("Rainy concert with 18,000 people at 7 PM")

    assert result.success
    assert result.parsed is not None
    assert result.parsed.crowdSize == 18000
    assert result.parsed.entryDistribution[0].gateId == "gate-e"
