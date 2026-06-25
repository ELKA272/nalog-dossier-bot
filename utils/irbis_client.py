import asyncio
from typing import Optional
import httpx
from config import IRBIS_API_TOKEN
from utils.logger import logger

BASE = "https://ir-bis.org"


class IrbisError(Exception):
    pass


class IrbisClient:
    """HTTP client for ir-bis.org API with token auth."""

    def __init__(self):
        self._client = httpx.AsyncClient(
            timeout=90,
            verify=False,
        )

    async def close(self):
        await self._client.aclose()

    async def _get(self, path: str, params: Optional[dict] = None) -> dict:
        url = f"{BASE}{path}"
        query = dict(params or {})
        query["token"] = IRBIS_API_TOKEN
        try:
            resp = await self._client.get(url, params=query)
            if resp.status_code == 401:
                raise IrbisError("Unauthorized: check IRBIS_API_TOKEN")
            if resp.status_code == 403:
                raise IrbisError("Forbidden: API access denied")
            if resp.status_code == 404:
                return {"error": "not_found", "raw": resp.text[:200]}
            if resp.status_code != 200:
                raise IrbisError(f"HTTP {resp.status_code}: {resp.text[:200]}")
            return resp.json()
        except httpx.TimeoutException:
            raise IrbisError(f"Timeout fetching {path}")

    async def create_check(self, inn: str) -> str:
        """Create a new check for a company or individual by INN.
        Returns UUID string.
        """
        if len(inn) == 12:
            logger.info(f"Creating people-check for INN {inn}")
            data = await self._get("/new/people-check.json", {
                "PeopleQuery.INN": inn,
                "PeopleQuery.LastName": ".",
                "PeopleQuery.FirstName": ".",
                "regions": ",".join(str(i) for i in range(1, 101)),
            })
        else:
            logger.info(f"Creating org-check for INN {inn}")
            data = await self._get("/new/org-check.json", {"inn": inn})

        uuid = data.get("uuid")
        if not uuid:
            raise IrbisError(f"Failed to create check: {data}")
        logger.info(f"Check created, UUID: {uuid}")
        return uuid

    async def wait_ready(self, uuid: str, endpoint: str = "org-egrul.json",
                         event: str = "result", timeout: int = 120,
                         version: Optional[str] = "4") -> None:
        """Poll until data is ready (response is present) or timeout."""
        path = f"/ru/base/-/services/report/{uuid}/{endpoint}"
        deadline = asyncio.get_event_loop().time() + timeout
        while True:
            params = {"event": event}
            if version:
                params["version"] = version
            data = await self._get(path, params)
            if data.get("response") is not None:
                return
            raw_wait = data.get("waitTime", 2000)
            wait = int(raw_wait) if raw_wait is not None else 2000
            if asyncio.get_event_loop().time() + max(wait / 1000, 2) > deadline:
                raise IrbisError(f"Timeout waiting for data (UUID: {uuid})")
            await asyncio.sleep(max(wait / 1000, 2) if wait else 3)

    async def get(self, uuid: str, path: str, event: str,
                  version: Optional[str] = None,
                  params: Optional[dict] = None):
        """Fetch data from a specific endpoint by UUID.
        Returns raw response (may contain status=-1 if not ready).
        """
        full_path = f"/ru/base/-/services/report/{uuid}/{path}"
        query = {"event": event}
        if version:
            query["version"] = version
        if params:
            query.update(params)
        data = await self._get(full_path, query)
        resp = data.get("response")
        return resp if resp is not None else data
