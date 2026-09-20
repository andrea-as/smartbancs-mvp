import asyncio
import time
import httpx
import os
import statistics

URL = "http://localhost:8000/api/v1/transfers"
AMOUNT = float(os.getenv("TRANSFER_AMOUNT", "0.01"))

async def one(client, i):
    if i % 2 == 0:
        source, destination = "ACC-1001", "ACC-1002"
    else:
        source, destination = "ACC-1002", "ACC-1001"
    start = time.perf_counter()
    try:
        response = await client.post(URL, json={
            "source_account": source,
            "destination_account": destination,
            "amount": AMOUNT,
            "currency": "USD"
        })
        return response.status_code, response.elapsed.total_seconds()
    except httpx.HTTPError:
        return 599, time.perf_counter() - start

async def main():
    total = int(os.getenv("TOTAL_REQUESTS", "50"))
    concurrency = int(os.getenv("CONCURRENCY", "50"))
    start = time.perf_counter()
    limits = httpx.Limits(max_connections=concurrency)
    async with httpx.AsyncClient(timeout=5, limits=limits) as client:
        semaphore = asyncio.Semaphore(concurrency)

        async def bounded(i):
            async with semaphore:
                return await one(client, i)

        results = await asyncio.gather(*(bounded(i) for i in range(total)))
    elapsed = time.perf_counter() - start
    report = {
        "requests": total,
        "concurrency": concurrency,
        "amount": AMOUNT,
        "elapsed_s": round(elapsed, 3),
        "observed_rps": round(total / elapsed, 2),
        "2xx": sum(200 <= status < 300 for status, _ in results),
        "other": sum(status >= 300 for status, _ in results),
        "p95_s": round(
            statistics.quantiles(
                [duration for _, duration in results], n=100
            )[94],
            4,
        ),
        "under_2s": sum(duration < 2 for _, duration in results),
        "failed_transport": sum(status == 599 for status, _ in results),
    }
    print(report)
    if os.getenv("FAIL_ON_SLO", "false").lower() == "true":
        if report["p95_s"] >= 2 or report["other"] > 0:
            raise SystemExit("SLO failed: p95 must be <2s and all requests must succeed")

if __name__ == "__main__":
    asyncio.run(main())
