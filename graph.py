import psycopg
from psycopg_pool import ConnectionPool

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, StateGraph

from agents import (
    budget_agent,
    final_response_agent,
    flight_agent,
    hotel_agent,
    human_approval_agent,
    itinerary_agent,
    supervisor_agent,
    weather_agent,
)

from config import DATABASE_URL
from state import TravelState


AGENT_ORDER = [
    "flight_agent",
    "hotel_agent",
    "weather_agent",
    "budget_agent",
    "itinerary_agent",
]


ROUTE_MAP = {
    "flight_agent": "flight_agent",
    "hotel_agent": "hotel_agent",
    "weather_agent": "weather_agent",
    "budget_agent": "budget_agent",
    "itinerary_agent": "itinerary_agent",
    "__end__": END,
}


def _selected_agents(state: TravelState) -> list[str]:
    selected = state.get("selected_agents") or []
    return [agent for agent in AGENT_ORDER if agent in selected]


def route_from_supervisor(state: TravelState) -> str:
    if state.get("is_valid") is False:
        return "__end__"

    selected = _selected_agents(state)
    return selected[0] if selected else "itinerary_agent"


def route_after_agent(current_agent: str):
    def route(state: TravelState) -> str:
        selected = _selected_agents(state)

        current_index = AGENT_ORDER.index(current_agent)

        for next_agent in AGENT_ORDER[current_index + 1:]:
            if next_agent in selected:
                return next_agent

        return "itinerary_agent"

    return route


def route_after_human_approval(state: TravelState) -> str:
    if state.get("approved"):
        return "final_response"
    return "itinerary_agent"


def build_graph():
    graph = StateGraph(TravelState)

    # Add nodes
    graph.add_node("supervisor", supervisor_agent)
    graph.add_node("flight_agent", flight_agent)
    graph.add_node("hotel_agent", hotel_agent)
    graph.add_node("weather_agent", weather_agent)
    graph.add_node("budget_agent", budget_agent)
    graph.add_node("itinerary_agent", itinerary_agent)
    graph.add_node("human_approval", human_approval_agent)
    graph.add_node("final_response", final_response_agent)

    # Start -> Supervisor
    graph.add_edge(START, "supervisor")

    # Supervisor -> selected agent
    graph.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        ROUTE_MAP,
    )

    # Agent routing
    graph.add_conditional_edges(
        "flight_agent",
        route_after_agent("flight_agent"),
        ROUTE_MAP,
    )

    graph.add_conditional_edges(
        "hotel_agent",
        route_after_agent("hotel_agent"),
        ROUTE_MAP,
    )

    graph.add_conditional_edges(
        "weather_agent",
        route_after_agent("weather_agent"),
        ROUTE_MAP,
    )

    graph.add_conditional_edges(
        "budget_agent",
        route_after_agent("budget_agent"),
        ROUTE_MAP,
    )

    # Itinerary -> Human approval
    graph.add_edge("itinerary_agent", "human_approval")

    # Conditional routing from Human approval:
    # If approved -> final_response -> END
    # If rejected with feedback -> loop back to itinerary_agent for revision
    graph.add_conditional_edges(
        "human_approval",
        route_after_human_approval,
        {
            "final_response": "final_response",
            "itinerary_agent": "itinerary_agent",
        },
    )

    graph.add_edge("final_response", END)

    # PostgreSQL checkpointer with auto-reconnecting ConnectionPool
    # (Resilient to serverless Neon SSL connection drops)
    if DATABASE_URL:
        try:
            pool = ConnectionPool(
                DATABASE_URL,
                min_size=1,
                max_size=10,
                max_idle=120.0,
                check=ConnectionPool.check_connection,
                kwargs={"autocommit": True},
            )
            pool.open()

            checkpointer = PostgresSaver(pool)
            checkpointer.setup()

            return graph.compile(
                checkpointer=checkpointer
            )
        except Exception as e:
            print(f"Warning: Could not connect to PostgreSQL checkpointer ({e}). Compiling in-memory.")
            return graph.compile()

    # If no DATABASE_URL is configured,
    # compile without persistent memory.
    return graph.compile()


app = build_graph()
