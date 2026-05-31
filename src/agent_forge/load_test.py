import asyncio
import time
import math
from agent_forge.agent import Agent

async def run_single_task(agent: Agent, task: str, index: int) -> dict:
    print(f"[Worker {index}] Starting Task: '{task}'")
    start = time.time()
    try:
        res = await agent.run(task)
        latency = time.time() - start
        success = "error" not in res.get("data", {})
        print(f"[Worker {index}] Completed in {latency:.2f}s | Success: {success}")
        return {"latency": latency, "success": success, "error": None}
    except Exception as e:
        latency = time.time() - start
        print(f"[Worker {index}] Failed after {latency:.2f}s | Error: {e}")
        return {"latency": latency, "success": False, "error": str(e)}

async def main():
    print("==================================================")
    print("Starting AgentForge Milestone 4 Concurrent Load Test")
    print("==================================================")

    agent = Agent(use_llm=True)
    if not agent.use_llm:
        print("ERROR: Agent cannot run in LLM mode. Verify GROQ_API_KEY in .env.")
        return

    # A set of tasks to execute concurrently
    load_tasks = [
        "Show me the users table schema",
        "Show me the file contents of README.md",
        "Summarize open PRs for owner samuelcolvin and FastAPI Repository",
        "List open PRs for pydantic/pydantic",
        "Summarize open PRs touching the users table"
    ]

    concurrency_level = len(load_tasks)
    print(f"Triggering {concurrency_level} requests concurrently...")

    start_total = time.time()
    results = await asyncio.gather(*(run_single_task(agent, task, i) for i, task in enumerate(load_tasks, 1)))
    total_duration = time.time() - start_total

    # Metrics Calculations
    latencies = [r["latency"] for r in results]
    successes = [r["success"] for r in results]
    successful_count = sum(1 for s in successes if s)
    
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
    sorted_latencies = sorted(latencies)
    p95_idx = math.ceil(0.95 * len(sorted_latencies)) - 1
    p95_latency = sorted_latencies[p95_idx] if sorted_latencies else 0.0

    throughput = concurrency_level / total_duration if total_duration > 0 else 0

    print("\n==================================================")
    print("LOAD TEST RESULT METRICS")
    print("==================================================")
    print(f"Total Requests Executed:    {concurrency_level}")
    print(f"Successful Requests:        {successful_count}/{concurrency_level} ({(successful_count/concurrency_level)*100:.1f}%)")
    print(f"Total Load Test Duration:   {total_duration:.2f}s")
    print(f"Throughput (Requests/sec):   {throughput:.2f} req/sec")
    print(f"Average Request Latency:    {avg_latency:.2f}s")
    print(f"p95 Request Latency:        {p95_latency:.2f}s")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(main())
