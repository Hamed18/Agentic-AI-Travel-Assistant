"""
Quick test to inspect LangGraph streaming updates structure
"""
import uuid
import sys
sys.stdout.reconfigure(encoding="utf-8")

from graph import build_graph
from langgraph.types import Command

app = build_graph()
thread_id = f"test-stream-{uuid.uuid4().hex[:6]}"
config = {"configurable": {"thread_id": thread_id}}

initial_state = {
    "user_query": "Plan a 1-day quick trip to Kyoto, Japan.",
    "user_id": "stream-tester",
    "messages": [],
    "approved": False,
    "human_feedback": "",
    "llm_calls": 0,
}

print(f"Starting test stream for thread {thread_id}...")
for chunk in app.stream(initial_state, config=config, stream_mode="updates"):
    for node_name, node_update in chunk.items():
        keys = list(node_update.keys()) if isinstance(node_update, dict) else []
        print(f"  --> Node completed: {node_name} | Updated state keys: {keys}")

state = app.get_state(config)
print(f"Stream paused. Next nodes: {state.next}")
if state.next:
    print("Interrupt detected as expected! Resuming with approval...")
    for chunk in app.stream(Command(resume={"approved": True, "feedback": ""}), config=config, stream_mode="updates"):
        for node_name, node_update in chunk.items():
            keys = list(node_update.keys()) if isinstance(node_update, dict) else []
            print(f"  --> Resume node completed: {node_name} | Updated state keys: {keys}")

print("Graph stream test finished successfully!")
