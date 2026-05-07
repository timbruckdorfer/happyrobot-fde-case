"""FMCSA QCMobile API wrapper with TTL caching.

Endpoint reference: https://mobile.fmcsa.dot.gov/QCDevsite/docs/getStarted
We hit `/carriers/docket-number/{docket}` which accepts an MC number.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx
import structlog

from app.core.settings import Settings, get_settings

log = structlog.get_logger("fmcsa")


@dataclass
class CarrierVerification:
    eligible: bool
    mc_number: str
    carrier_name: str | None
    dot_number: str | None
    allowed_to_operate: str | None
    operating_status: str | None
    reasons: list[str]
    raw: dict[str, Any] | None = None


class _TTLCache:
    def __init__(self, ttl_seconds: int) -> None:
        self.ttl = ttl_seconds
        self._store: dict[str, tuple[float, CarrierVerification]] = {}

    def get(self, key: str) -> CarrierVerification | None:
        item = self._store.get(key)
        if not item:
            return None
        ts, value = item
        if time.time() - ts > self.ttl:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: CarrierVerification) -> None:
        self._store[key] = (time.time(), value)


class FMCSAClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._cache = _TTLCache(self.settings.fmcsa_cache_ttl_seconds)

    @staticmethod
    def _normalize_mc(mc_number: str) -> str:
        return "".join(ch for ch in mc_number.strip().upper() if ch.isdigit())

    async def verify(self, mc_number: str) -> CarrierVerification:
        normalized = self._normalize_mc(mc_number)
        if not normalized:
            return CarrierVerification(
                eligible=False,
                mc_number=mc_number,
                carrier_name=None,
                dot_number=None,
                allowed_to_operate=None,
                operating_status=None,
                reasons=["MC number is empty or invalid"],
            )

        cached = self._cache.get(normalized)
        if cached:
            return cached

        if not self.settings.fmcsa_api_key:
            log.warning("fmcsa_api_key_missing")
            result = CarrierVerification(
                eligible=False,
                mc_number=normalized,
                carrier_name=None,
                dot_number=None,
                allowed_to_operate=None,
                operating_status=None,
                reasons=["FMCSA API key not configured on server"],
            )
            return result

        url = f"{self.settings.fmcsa_base_url}/carriers/docket-number/{normalized}"
        params = {"webKey": self.settings.fmcsa_api_key}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
            if resp.status_code != 200:
                log.warning("fmcsa_non_200", status=resp.status_code, body=resp.text[:200])
                return CarrierVerification(
                    eligible=False,
                    mc_number=normalized,
                    carrier_name=None,
                    dot_number=None,
                    allowed_to_operate=None,
                    operating_status=None,
                    reasons=[f"FMCSA returned HTTP {resp.status_code}"],
                )
            payload = resp.json()
        except httpx.HTTPError as exc:
            log.exception("fmcsa_http_error")
            return CarrierVerification(
                eligible=False,
                mc_number=normalized,
                carrier_name=None,
                dot_number=None,
                allowed_to_operate=None,
                operating_status=None,
                reasons=[f"FMCSA request failed: {exc!s}"],
            )

        result = self._parse(normalized, payload)
        self._cache.set(normalized, result)
        return result

    @staticmethod
    def _parse(mc_number: str, payload: dict[str, Any]) -> CarrierVerification:
        content = payload.get("content")
        if not content:
            return CarrierVerification(
                eligible=False,
                mc_number=mc_number,
                carrier_name=None,
                dot_number=None,
                allowed_to_operate=None,
                operating_status=None,
                reasons=["No carrier found for that MC number"],
                raw=payload,
            )
        first = content[0] if isinstance(content, list) else content
        carrier = first.get("carrier", first) if isinstance(first, dict) else {}

        allowed = carrier.get("allowedToOperate")
        status = carrier.get("statusCode")
        name = carrier.get("legalName") or carrier.get("dbaName")
        dot = str(carrier.get("dotNumber")) if carrier.get("dotNumber") is not None else None

        reasons: list[str] = []
        eligible = True

        if allowed not in ("Y", True, "true"):
            eligible = False
            reasons.append(f"FMCSA allowedToOperate={allowed}")
        if status and status not in ("A",):
            eligible = False
            reasons.append(f"FMCSA statusCode={status}")

        return CarrierVerification(
            eligible=eligible,
            mc_number=mc_number,
            carrier_name=name,
            dot_number=dot,
            allowed_to_operate=str(allowed) if allowed is not None else None,
            operating_status=status,
            reasons=reasons,
            raw=payload,
        )
