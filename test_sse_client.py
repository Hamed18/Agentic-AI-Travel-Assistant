"""
test_sse_client.py - Real-time SSE Stream Consumer Test
Tests the /api/chat/stream and /api/chat/resume endpoints
"""

import sys
import json
import httpx
sys.stdout.reconfigure(encoding="utf-8")

URL = "http://localhost:8000/api/chat/stream"
RESUME_URL = "http://localhost:8000/api/chat/resume"

def test_stream():
    payload = {
        "query": "Plan a 1-day budget day trip to Kyoto.",
        "thread_id": "test_sse_user_1",
        "user_id": "sse_tester"
    }

    print("=" * 60)
    print("🚀 CONNECTING TO FASTAPI SSE CHAT STREAM")
    print(f"URL: {URL}")
    print(f"Payload: {payload}")
    print("=" * 60)

    draft_itinerary = ""
    thread_id = payload["thread_id"]
    hit_interrupt = False

    with httpx.Client(timeout=120.0) as client:
        with client.stream("POST", URL, json=payload) as response:
            print(f"HTTP Status: {response.status_code}")
            event_type = None

            for line in response.iter_lines():
                if not line:
                    continue
                if line.startswith("event:"):
                    event_type = line.replace("event:", "").strip()
                elif line.startswith("data:"):
                    raw_data = line.replace("data:", "").strip()
                    try:
                        data = json.loads(raw_data)
                    except Exception:
                        data = raw_data

                    print(f"\n[SSE EVENT: {event_type}]")
                    if isinstance(data, dict):
                        node = data.get("node")
                        if node:
                            print(f"  Stage Node: {node}")
                        if "selected_agents" in data:
                            print(f"  Selected Agents: {data['selected_agents']}")
                        if "draft_itinerary" in data:
                            draft_itinerary = data["draft_itinerary"]
                            print(f"  Draft Preview (first 120 chars): {draft_itinerary[:120]}...")
                        if event_type == "interrupt":
                            hit_interrupt = True
                            print("  ⚠️ HIT HUMAN-IN-THE-LOOP INTERRUPT! Approval required.")
                    else:
                        print(f"  Data: {data}")

    if hit_interrupt:
        print("\n" + "=" * 60)
        print("🙋 RESUMING PAUSED STREAM VIA /api/chat/resume (Approved=True)")
        print("=" * 60)

        resume_payload = {
            "thread_id": thread_id,
            "approved": True,
            "feedback": ""
        }

        with httpx.Client(timeout=120.0) as client:
            with client.stream("POST", RESUME_URL, json=resume_payload) as response:
                print(f"Resume HTTP Status: {response.status_code}")
                event_type = None

                for line in response.iter_lines():
                    if not line:
                        continue
                    if line.startswith("event:"):
                        event_type = line.replace("event:", "").strip()
                    elif line.startswith("data:"):
                        raw_data = line.replace("data:", "").strip()
                        try:
                            data = json.loads(raw_data)
                        except Exception:
                            data = raw_data

                        print(f"\n[RESUME SSE EVENT: {event_type}]")
                        if isinstance(data, dict) and "final_response" in data:
                            print(f"  Final Response Preview: {data['final_response'][:150]}...")
                        elif isinstance(data, dict) and "node" in data:
                            print(f"  Stage: {data['node']}")

    print("\n" + "=" * 60)
    print("✅ SSE STREAMING & HUMAN APPROVAL CYCLE TEST COMPLETED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    test_stream()
