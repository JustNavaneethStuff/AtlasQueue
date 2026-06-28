from __future__ import annotations

import asyncio
import os
import time

import httpx


async def main() -> None:
    base_url = os.environ.get("BENCHMARK_API_URL", "http://localhost:8000")
    api_key = os.environ.get("API_KEY", "dev-api-key")
    iterations = int(os.environ.get("BENCHMARK_ITERATIONS", "50"))
    headers = {"X-API-Key": api_key, "Content-Type": "application/json"}

    async with httpx.AsyncClient(base_url=base_url, headers=headers, timeout=30.0) as client:
        latencies: list[float] = []
        for i in range(iterations):
            start = time.perf_counter()
            response = await client.post("/v1/tasks", json={"name": "echo", "payload": {"i": i}})
            latencies.append(time.perf_counter() - start)
            response.raise_for_status()

    latencies.sort()
    p50 = latencies[len(latencies) // 2]
    p95 = latencies[int(len(latencies) * 0.95) - 1]
    print(f"iterations={iterations}")
    print(f"p50={p50:.4f}s p95={p95:.4f}s max={max(latencies):.4f}s")


if __name__ == "__main__":
    asyncio.run(main())
