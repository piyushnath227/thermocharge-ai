from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import httpx


class FortyGuardError(RuntimeError):
    pass


class FortyGuardClient:
    BASE_URL = 'https://api.fortyguard.com'

    def __init__(self, api_key: str, timeout: float = 30.0):
        if not api_key:
            raise ValueError('FortyGuard API key is required')
        self.headers = {'api-key': api_key, 'Content-Type': 'application/json'}
        self.timeout = timeout

    async def _post(
        self, endpoint: str, payload: dict[str, Any], *, max_retries: int = 3, retry_backoff: float = 3.0
    ) -> str:
        response = None
        for attempt in range(1, max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(f'{self.BASE_URL}{endpoint}', headers=self.headers, json=payload)
                break
            except httpx.TransportError as exc:
                if attempt == max_retries:
                    raise FortyGuardError(
                        f'{endpoint} failed after {max_retries} attempts due to a connection error '
                        f'({exc.__class__.__name__}: {exc}). This looks like a local network/DNS blip, '
                        f'not a FortyGuard API error — check connectivity and re-run.'
                    ) from exc
                wait = retry_backoff * attempt
                print(
                    f'  [retry] {endpoint} connection error ({exc.__class__.__name__}); '
                    f'retrying in {wait:.0f}s (attempt {attempt}/{max_retries})...'
                )
                await asyncio.sleep(wait)
        if response.status_code != 200:
            raise FortyGuardError(f'{endpoint} returned HTTP {response.status_code}: {response.text}')
        body = response.json()
        activity_id = body.get('data', {}).get('activity_id')
        if not activity_id:
            raise FortyGuardError(f'No activity_id returned: {json.dumps(body)}')
        return activity_id

    async def poll(self, activity_id: str, *, max_wait_seconds: int = 300, interval_seconds: int = 3) -> dict[str, Any]:
        start = asyncio.get_running_loop().time()
        deadline = start + max_wait_seconds
        next_heartbeat = start + 30
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            while asyncio.get_running_loop().time() < deadline:
                try:
                    response = await client.get(
                        f'{self.BASE_URL}/v1/status/{activity_id}', headers=self.headers
                    )
                except httpx.HTTPError:
                    await asyncio.sleep(interval_seconds)
                    continue

                if response.status_code >= 500:
                    await asyncio.sleep(interval_seconds)
                    continue
                if response.status_code != 200:
                    raise FortyGuardError(
                        f'Status check returned HTTP {response.status_code}: {response.text}'
                    )

                body = response.json()
                status = body.get('data', {}).get('status')
                if status == 'Completed':
                    return body
                if status == 'Failed':
                    raise FortyGuardError(f'Activity {activity_id} failed: {json.dumps(body)}')

                now = asyncio.get_running_loop().time()
                if now >= next_heartbeat:
                    print(
                        f'  ... still waiting on activity {activity_id} '
                        f'(status: {status or "Pending"}, {int(now - start)}s elapsed)'
                    )
                    next_heartbeat = now + 30

                await asyncio.sleep(interval_seconds)

        raise FortyGuardError(f'Activity {activity_id} did not complete within {max_wait_seconds}s')

    async def heatmap(self, payload: dict[str, Any]) -> dict[str, Any]:
        activity_id = await self._post('/v1/heatmap', payload)
        return await self.poll(activity_id)

    async def env_params(self, payload: dict[str, Any]) -> dict[str, Any]:
        activity_id = await self._post('/v1/env_params', payload)
        return await self.poll(activity_id)


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding='utf-8')