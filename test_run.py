"""
test_run.py  –  End-to-end benchmark for the Agentic AI Travel Assistant.
Usage:
    python test_run.py
Reports per-stage latency, token counts (where available), and any errors.
"""

import sys, time, uuid, json, traceback, textwrap, os
from langgraph.types import Command
sys.stdout.reconfigure(encoding="utf-8")

# ─── helpers ───────────────────────────────────────────────────────────────────

def fmt(seconds: float) -> str:
    return f"{seconds:.2f}s"

def hr(char="─", width=70):
    print(char * width)

# ─── patch agents to measure per-node latency ─────────────────────────────────

import agents as _agents_module

_timings: dict[str, float] = {}

_ORIGINAL_FUNCS = {}

def _timed(name, fn):
    def wrapper(state):
        t0 = time.perf_counter()
        result = fn(state)
        elapsed = time.perf_counter() - t0
        _timings[name] = elapsed
        print(f"  ✔  {name:<30}  {fmt(elapsed)}")
        return result
    return wrapper

# Patch each agent function
for _name in ["supervisor_agent", "flight_agent", "hotel_agent",
              "weather_agent", "budget_agent", "itinerary_agent",
              "human_approval_agent", "final_response_agent"]:
    _orig = getattr(_agents_module, _name)
    _ORIGINAL_FUNCS[_name] = _orig
    setattr(_agents_module, _name, _timed(_name, _orig))

# Now import graph (which imports agents), so patched functions are used
from graph import build_graph
from pdf_generator import create_pdf

# ─── test cases ───────────────────────────────────────────────────────────────

SAMPLE_QUERIES = [
    "Plan a 5-day budget trip to Tokyo, Japan for 2 people with a total budget of $3000.",
    "I want a 3-day luxury weekend in Paris, France. Budget is flexible.",
]

# ─── run ──────────────────────────────────────────────────────────────────────

def run_query(query: str, query_index: int):
    hr("═")
    print(f"TEST {query_index}: {query}")
    hr()

    _timings.clear()

    thread_id = str(uuid.uuid4())
    initial_state = {
        "user_query": query,
        "user_id": "test-user",
        "messages": [],
        "approved": True,          # skip human-in-the-loop for automated test
        "human_feedback": "",
        "llm_calls": 0,
    }

    results = {
        "query": query,
        "errors": [],
        "stage_latency": {},
        "total_latency": 0.0,
        "pdf_latency": 0.0,
        "pdf_size_kb": 0.0,
        "final_response_preview": "",
    }

    try:
        app = build_graph()

        print("\n[STAGE LATENCIES]")
        t_total_start = time.perf_counter()

        output = None
        config = {"configurable": {"thread_id": thread_id}}

        # ── First pass: run until interrupt (human_approval_agent) ────────────
        for chunk in app.stream(initial_state, config=config, stream_mode="values"):
            output = chunk

        # ── Detect interrupt and resume with approval ──────────────────────────
        # LangGraph interrupt() pauses graph; we must resume to reach final_response_agent
        state_snapshot = app.get_state(config)
        if state_snapshot.next:  # graph is interrupted/paused
            print(f"  ℹ  Interrupt detected at: {state_snapshot.next} — resuming with approval")
            resume_payload = {"approved": True, "feedback": ""}
            for chunk in app.stream(
                Command(resume=resume_payload),
                config=config,
                stream_mode="values",
            ):
                output = chunk

        total_time = time.perf_counter() - t_total_start

        results["stage_latency"] = dict(_timings)
        results["total_latency"] = total_time

        if output:
            final = output.get("final_response", "") or output.get("itinerary", "")
            results["final_response_preview"] = final[:500]

            # ── PDF generation test ──────────────────────────────────────────
            if final:
                print("\n[PDF GENERATION]")
                t_pdf = time.perf_counter()
                try:
                    pdf_bytes = create_pdf(final)
                    pdf_elapsed = time.perf_counter() - t_pdf
                    results["pdf_latency"] = pdf_elapsed
                    results["pdf_size_kb"] = len(pdf_bytes) / 1024
                    print(f"  ✔  PDF generated  {fmt(pdf_elapsed)}  ({results['pdf_size_kb']:.1f} KB)")
                    # Save to disk for manual inspection
                    os.makedirs("scratch", exist_ok=True)
                    out_path = f"scratch/test_output_query_{query_index}.pdf"
                    with open(out_path, "wb") as f:
                        f.write(pdf_bytes)
                    print(f"  ✔  Saved to {out_path}")
                except Exception as e:
                    err = f"PDF generation failed: {e}"
                    results["errors"].append(err)
                    print(f"  ✘  {err}")

    except Exception as e:
        tb = traceback.format_exc()
        results["errors"].append(f"Pipeline error: {e}\n{tb}")
        print(f"\n  ✘  Pipeline error: {e}")
        traceback.print_exc()

    # ── summary ───────────────────────────────────────────────────────────────
    hr()
    print(f"\n[SUMMARY — Query {query_index}]")
    print(f"  Total pipeline time : {fmt(results['total_latency'])}")
    print(f"  PDF generation time : {fmt(results['pdf_latency'])}")
    print(f"  PDF size            : {results['pdf_size_kb']:.1f} KB")

    if results["stage_latency"]:
        slowest = max(results["stage_latency"].items(), key=lambda x: x[1])
        print(f"  Slowest stage       : {slowest[0]}  ({fmt(slowest[1])})")

    if results["errors"]:
        print(f"\n  ⚠  ERRORS ({len(results['errors'])}):")
        for e in results["errors"]:
            print(textwrap.indent(e, "     "))

    if results["final_response_preview"]:
        print(f"\n[RESPONSE PREVIEW — first 500 chars]")
        print(textwrap.indent(results["final_response_preview"], "  "))

    return results


def main():
    all_results = []
    for i, q in enumerate(SAMPLE_QUERIES, 1):
        r = run_query(q, i)
        all_results.append(r)
        print()

    # ── aggregate report ──────────────────────────────────────────────────────
    hr("═")
    print("AGGREGATE REPORT")
    hr()
    for r in all_results:
        q_short = r["query"][:60] + "..." if len(r["query"]) > 60 else r["query"]
        status = "✔" if not r["errors"] else "✘"
        print(f"  {status}  [{fmt(r['total_latency'])} pipeline | {fmt(r['pdf_latency'])} PDF]  {q_short}")

    # ── issues log ────────────────────────────────────────────────────────────
    has_issues = any(r["errors"] for r in all_results)
    if has_issues:
        print("\n[ISSUES FOUND]")
        for r in all_results:
            if r["errors"]:
                print(f"\n  Query: {r['query'][:80]}")
                for e in r["errors"]:
                    print(f"    - {e[:200]}")

    # ── latency analysis ──────────────────────────────────────────────────────
    print("\n[LATENCY ANALYSIS]")
    all_stages = {}
    for r in all_results:
        for stage, t in r["stage_latency"].items():
            all_stages.setdefault(stage, []).append(t)

    for stage, times in sorted(all_stages.items(), key=lambda x: -sum(x[1])):
        avg = sum(times) / len(times)
        mx  = max(times)
        flag = "  ⚠  SLOW" if avg > 10 else ""
        print(f"  {stage:<35} avg={fmt(avg)}  max={fmt(mx)}{flag}")

    hr("═")
    print("Test run complete.")


if __name__ == "__main__":
    main()
