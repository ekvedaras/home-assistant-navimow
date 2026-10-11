"""Run with: python tests/test_token_refresh.py (needs homeassistant and paho-mqtt installed)."""
import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from custom_components.navimow.coordinator import NavimowDataUpdateCoordinator


class FakeApi:
    def __init__(self, responses):
        self._token = "access-0"
        self.used_refresh_tokens = []
        self._responses = iter(responses)

    async def async_refresh_token(self, refresh_token):
        self.used_refresh_tokens.append(refresh_token)
        await asyncio.sleep(0.01)
        return next(self._responses)


def make_coordinator(responses):
    coordinator = NavimowDataUpdateCoordinator.__new__(NavimowDataUpdateCoordinator)
    coordinator.api = FakeApi(responses)
    coordinator.entry = SimpleNamespace(data={"access_token": "access-0", "refresh_token": "refresh-0"})
    coordinator.hass = SimpleNamespace(
        config_entries=SimpleNamespace(
            async_update_entry=lambda entry, data: setattr(entry, "data", data)
        )
    )
    coordinator._token_expires_at = 0
    coordinator._token_lock = asyncio.Lock()
    return coordinator


async def demo():
    coordinator = make_coordinator(
        [{"access_token": "access-1", "refresh_token": "refresh-1", "expires_in": "3600"}]
    )
    results = await asyncio.gather(
        coordinator._async_ensure_valid_token(),
        coordinator._async_ensure_valid_token(),
        coordinator._async_ensure_valid_token(force=True),
    )
    assert results == [True, True, True]
    assert coordinator.api.used_refresh_tokens == ["refresh-0"], coordinator.api.used_refresh_tokens
    assert coordinator.api._token == "access-1"
    assert coordinator.entry.data["refresh_token"] == "refresh-1"

    assert await coordinator._async_ensure_valid_token() is True
    assert coordinator.api.used_refresh_tokens == ["refresh-0"], "valid token must not be refreshed"

    coordinator = make_coordinator([{"code": 4005, "desc": "TOKEN_EXPIRED"}, {}])
    assert await coordinator._async_ensure_valid_token() is False
    assert await coordinator._async_ensure_valid_token(force=True) is False
    assert coordinator.entry.data["refresh_token"] == "refresh-0"
    assert coordinator.api._token == "access-0"

    print("ok")


if __name__ == "__main__":
    asyncio.run(demo())
