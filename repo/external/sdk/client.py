import os, httpx, asyncio
from typing import Dict, Any, Optional, List, Union, Sequence, Set

class SheratanClient:
    DEFAULT_RETRY_STATUSES = {408, 425, 429, 500, 502, 503, 504}

    def __init__(
        self,
        api_base: Optional[str] = None,
        timeout: Union[float, httpx.Timeout] = 60.0,
        max_retries: int = 3,
        backoff_factor: float = 1.5,
        max_retry_wait: float = 10.0,
        retry_statuses: Optional[Sequence[int]] = None,
    ) -> None:
        self.api_base = api_base or os.getenv("SHERATAN_API_BASE", "http://localhost:6060")
        self.timeout = timeout if isinstance(timeout, httpx.Timeout) else httpx.Timeout(timeout)
        self.max_retries = max(0, int(max_retries))
        self.backoff_factor = max(0.0, float(backoff_factor)) or 1.0
        self.max_retry_wait = max(0.0, float(max_retry_wait))
        self.retry_statuses: Set[int] = set(retry_statuses or self.DEFAULT_RETRY_STATUSES)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        attempt = 0
        wait_time = self.backoff_factor
        cap = self.max_retry_wait if self.max_retry_wait > 0 else None

        async with httpx.AsyncClient(base_url=self.api_base, timeout=self.timeout) as client:
            while True:
                try:
                    response = await client.request(method, path, json=json, params=params)
                    if response.status_code in self.retry_statuses and attempt < self.max_retries:
                        raise httpx.HTTPStatusError(
                            "Retryable response", request=response.request, response=response
                        )
                    response.raise_for_status()
                    return response.json()
                except httpx.HTTPStatusError as exc:
                    status_code = exc.response.status_code if exc.response is not None else None
                    retryable = status_code in self.retry_statuses if status_code is not None else False
                    if not retryable or attempt >= self.max_retries:
                        raise
                except httpx.TransportError:
                    if attempt >= self.max_retries:
                        raise
                attempt += 1
                sleep_for = min(wait_time, cap) if cap is not None else wait_time
                await asyncio.sleep(sleep_for)
                wait_time = min(wait_time * 2, cap) if cap is not None else wait_time * 2

    async def complete(self, model: str, prompt: str, max_tokens: int = 128) -> Dict[str, Any]:
        payload = {"model": model, "prompt": prompt, "max_tokens": max_tokens}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(f"{self.api_base}/api/v1/llm/complete", json=payload)
            r.raise_for_status()
            return r.json()

    async def submit_job(self, model: str, prompt: str, max_tokens: int = 128) -> Dict[str, Any]:
        payload = {"model": model, "prompt": prompt, "max_tokens": max_tokens}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(f"{self.api_base}/api/v1/jobs", json=payload)
            r.raise_for_status()
            return r.json()

    async def get_job(self, job_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(f"{self.api_base}/api/v1/jobs/{job_id}")
            r.raise_for_status()
            return r.json()

    async def watch_job(self, job_id: str, interval: float = 2.0, terminal_states: Optional[List[str]] = None) -> Dict[str, Any]:
        terminal_states = terminal_states or ["succeeded", "failed", "cancelled", "completed"]
        while True:
            job = await self.get_job(job_id)
            status = job.get("status")
            if status is None or status.lower() in terminal_states:
                return job
            await asyncio.sleep(interval)

    async def router_health(self) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(f"{self.api_base}/api/v1/router/health")
            r.raise_for_status()
            return r.json()

    async def list_models(self) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(f"{self.api_base}/api/v1/models")
            r.raise_for_status()
            return r.json()
