import asyncio
import json
import os
import time
import math
from pathlib import Path
from agent_forge.agent import Agent

# Token Pricing Constants for llama-3.3-70b-specdec
PRICE_INPUT_1M = 0.59
PRICE_OUTPUT_1M = 0.79

async def run_evaluation():
    print("==================================================")
    print("Starting AgentForge Milestone 4 Evaluation Suite")
    print("==================================================")

    # Initialize Agent with real LLM enabled
    agent = Agent(use_llm=True)
    if not agent.use_llm:
        print("ERROR: Agent cannot run in LLM mode. Please verify GROQ_API_KEY or OPENAI_API_KEY is configured in your .env file.")
        return

    # Load scenarios
    scenarios_path = Path(__file__).parent.parent.parent / "tests" / "eval_scenarios.json"
    if not scenarios_path.exists():
        scenarios_path = Path("tests/eval_scenarios.json")

    with open(scenarios_path, "r") as f:
        scenarios = json.load(f)

    results = []
    total_latency = 0.0
    total_cost = 0.0
    successful_tasks = 0
    total_f1 = 0.0

    print(f"Loaded {len(scenarios)} scenarios.")
    print("Running tasks sequentially to prevent API rate limiting...\n")

    for idx, scenario in enumerate(scenarios, 1):
        task_id = scenario["id"]
        task_text = scenario["task"]
        expected_tools = scenario["expected_tools"]
        expected_keywords = scenario["expected_keywords"]
        category = scenario["category"]

        print(f"[{idx}/{len(scenarios)}] Running Scenario {task_id} ({category}): '{task_text}'")

        start_time = time.time()
        agent_res = await agent.run(task_text)
        latency = time.time() - start_time

        steps = agent_res.get("steps_executed", [])
        actual_tools = [step["tool"] for step in steps]

        # Calculate Tool-Call Precision, Recall, and F1-score
        expected_set = set(expected_tools)
        actual_set = set(actual_tools)

        if expected_set and actual_set:
            intersection = expected_set & actual_set
            precision = len(intersection) / len(actual_set)
            recall = len(intersection) / len(expected_set)
            f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        elif not expected_set and not actual_set:
            f1 = 1.0
        else:
            f1 = 0.0

        # Calculate Task Success: Check if all expected keywords are present in the final summary
        summary = agent_res.get("summary", "")
        summary_lower = summary.lower()
        success = True
        for keyword in expected_keywords:
            if keyword.lower() not in summary_lower:
                success = False
                break

        # Calculate Token Cost
        usage = agent_res.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        cost = ((prompt_tokens * PRICE_INPUT_1M) + (completion_tokens * PRICE_OUTPUT_1M)) / 1_000_000.0

        results.append({
            "id": task_id,
            "category": category,
            "task": task_text,
            "expected_tools": expected_tools,
            "actual_tools": actual_tools,
            "f1_score": f1,
            "success": success,
            "latency": latency,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost": cost
        })

        # Update accumulators
        total_latency += latency
        total_cost += cost
        if success:
            successful_tasks += 1
        total_f1 += f1

        print(f"      F1 Score: {f1:.2f} | Success: {success} | Latency: {latency:.2f}s | Cost: ${cost:.6f}\n")
        
        # Short cooldown to avoid rate limits
        await asyncio.sleep(0.3)

    # Compute aggregate metrics
    num_scenarios = len(scenarios)
    success_rate = (successful_tasks / num_scenarios) * 100 if num_scenarios > 0 else 0
    avg_f1 = (total_f1 / num_scenarios) * 100 if num_scenarios > 0 else 0
    avg_latency = total_latency / num_scenarios if num_scenarios > 0 else 0
    
    # Calculate p95 Latency
    sorted_latencies = sorted([r["latency"] for r in results])
    p95_idx = math.ceil(0.95 * len(sorted_latencies)) - 1
    p95_latency = sorted_latencies[p95_idx] if sorted_latencies else 0.0

    print("==================================================")
    print("EVALUATION COMPLETED SUCCESSFULLY")
    print("==================================================")
    print(f"Overall Task Success Rate:  {success_rate:.1f}%")
    print(f"Average Tool Call F1 Score: {avg_f1:.1f}%")
    print(f"Mean Latency:               {avg_latency:.2f}s")
    print(f"p95 Latency:                {p95_latency:.2f}s")
    print(f"Total Model Cost:           ${total_cost:.6f}")
    print(f"Average Cost per Task:      ${(total_cost / num_scenarios):.6f}")
    print("==================================================")

    # Generate Markdown Report
    report_markdown = f"""# Evaluation Harness Report - Milestone 4

This report documents the quantitative performance metrics of the **AgentForge** orchestrator across a suite of 20 tasks, powered by a real-world **Groq Llama 3** model.

## Aggregated Performance Summary

| Metric | Value |
|---|---|
| **Total Scenarios** | {num_scenarios} |
| **Task Success Rate** | **{success_rate:.1f}%** |
| **Average Tool Call F1 Score** | **{avg_f1:.1f}%** |
| **Mean Latency** | {avg_latency:.2f}s |
| **p95 Latency** | {p95_latency:.2f}s |
| **Total Evaluation Cost** | ${total_cost:.6f} |
| **Average Cost per Task** | ${(total_cost / num_scenarios):.6f} |

---

## Detailed Scenario Breakdown

| Scenario ID | Category | Task | Expected Tools | Actual Tools | Tool F1 | Success | Latency | Cost |
|---|---|---|---|---|---|---|---|---|
"""
    for r in results:
        expected_str = ", ".join(r["expected_tools"]) if r["expected_tools"] else "None"
        actual_str = ", ".join(r["actual_tools"]) if r["actual_tools"] else "None"
        report_markdown += (
            f"| `{r['id']}` | `{r['category']}` | \"{r['task']}\" | `{expected_str}` | `{actual_str}` | "
            f"{r['f1_score']:.2f} | {'✅ Pass' if r['success'] else '❌ Fail'} | {r['latency']:.2f}s | ${r['cost']:.6f} |\n"
        )

    # Save to artifacts directory
    artifacts_dir = Path(__file__).parent.parent.parent / "artifacts"
    if not artifacts_dir.exists():
        artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    report_path = artifacts_dir / "eval_report.md"
    with open(report_path, "w") as f:
        f.write(report_markdown)

    print(f"Saved detailed evaluation report to {report_path.absolute()}")

if __name__ == "__main__":
    asyncio.run(run_evaluation())
