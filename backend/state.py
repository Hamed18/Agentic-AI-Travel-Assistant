from typing import Annotated, Any, TypedDict, Optional
import operator
from langchain_core.messages import AnyMessage

class TravelState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], operator.add]
    user_id: str
    owner_id: str
    user_query: str

    episodic_context: str
    tenant_docs_context: str
    user_profile_context: str

    trip_constraints: dict[str, Any]
    selected_agents: list[str]
    supervisor_reasoning: str

    flight_results: str
    hotel_results: str
    weather_results: str
    budget_results: str
    itinerary: str

    approval_request: str
    human_feedback: str
    approved: bool

    final_response: str
    direct_response: str
    intent: str
    response_type: str
    active_stages: list[str]
    llm_calls: int
    is_valid: bool
