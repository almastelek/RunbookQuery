import asyncio
import aiohttp
import time
import random

QUERIES = [
    "CrashLoopBackOff",
    "503 unavailable",
    "OOMKilled",
    "readiness probe",
    "memory limit",
    "deployment failed",
    "container crash",
    "prometheus rules",
    "grafana dashboard",
    "network policy",
    "Hi",
    "error 137",
    "latency high",
    "connection timeout",
    "pod stuck terminating"
]

async def send_request(session, i):
    query = random.choice(QUERIES)
    try:
        start = time.time()
        async with session.post(
            "http://127.0.0.1:8000/search",
            json={"query": query, "top_k": 5},
            timeout=10.0
        ) as response:
            duration = time.time() - start
            text = await response.text()
            if response.status != 200:
                print(f"Req {i}: Failed {response.status} - {text[:50]}")
            else:
                pass
                # print(f"Req {i}: Success ({duration:.2f}s)")
            return response.status
    except Exception as e:
        print(f"Req {i}: Error - {str(e)}")
        return 0

async def main():
    print("Starting stress test...")
    async with aiohttp.ClientSession() as session:
        # Run 50 concurrent requests
        tasks = []
        for i in range(50):
            tasks.append(send_request(session, i))
            await asyncio.sleep(0.05) # Ramp up slightly
        
        results = await asyncio.gather(*tasks)
        
        success = results.count(200)
        failed = len(results) - success
        print(f"\nCompleted. Success: {success}, Failed: {failed}")

if __name__ == "__main__":
    asyncio.run(main())
