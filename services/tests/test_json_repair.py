from gateway_service.ai_gateway import AIGateway


def test_parse_json_with_repair_and_smart_quotes():
    # Simulate LLM output with smart quotes and trailing comma
    text = 'final: {“score”: 0.8, “assessed_depth”: “Intermediate”,}'
    parsed = AIGateway._parse_json_like(text)
    assert parsed == {"score": 0.8, "assessed_depth": "Intermediate"}

