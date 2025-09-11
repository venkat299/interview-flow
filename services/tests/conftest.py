import pytest


@pytest.fixture(scope="session", autouse=True)
def disable_llm_health_check():
    """Disable LLM connectivity checks during tests."""
    from gateway_service import gateway
    mp = pytest.MonkeyPatch()

    async def _noop():
        return None

    mp.setattr(gateway, "health_check_active_providers", _noop)
    yield
    mp.undo()
