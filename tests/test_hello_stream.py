import os
import sys
import uuid

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT_DIR, "backend"))

from graph import app as graph_app

thread_id = f"test_{uuid.uuid4().hex[:8]}"
config = {"configurable": {"thread_id": thread_id}}

initial_state = {
    "user_query": "hello",
    "user_id": "test_user",
    "messages": [],
    "flight_results": "",
    "hotel_results": "",
    "weather_results": "",
    "budget_results": "",
    "itinerary": "",
    "final_response": "",
    "approved": False,
    "human_feedback": "",
    "llm_calls": 0,
}

print(f"Testing stream for thread: {thread_id} with query: 'hello'")
for chunk in graph_app.stream(initial_state, config=config, stream_mode="updates"):
    for node_name, node_update in chunk.items():
        print(f"\n--- Node Completed: {node_name} ---")
        if isinstance(node_update, dict):
            for k, v in node_update.items():
                if k in ["intent", "is_valid", "response_type", "selected_agents", "direct_response", "final_response"]:
                    print(f"  {k}: {str(v)[:100]}")

snapshot = graph_app.get_state(config)
print("\nFinal Snapshot Next:", snapshot.next)
print("Final Snapshot Values:")
for k in ["intent", "response_type", "is_valid", "final_response", "itinerary"]:
    print(f"  {k}: {str(snapshot.values.get(k))[:100]}")
