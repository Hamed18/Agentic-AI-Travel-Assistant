import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

import asyncio
import json
import re
import sys
import time
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.types import interrupt
from openai import RateLimitError, APIStatusError

from config import get_llm, get_fallback_llm
from mcp_client import current_weather, forecast, list_airlines, list_airports, tavily_search
from state import TravelState

# Primary Distributed LLM (Groq GPT-OSS 120B -> Google Gemini 3.5 Flash Lite)
llm = get_llm()
# Fast Distributed LLM (Groq Qwen 27B -> Google Gemini 3.5 Flash Lite)
_fast_llm = get_fallback_llm()

def _llm_text(system: str, prompt: str) -> str:
    """Invoke Heavy Distributed LLM with automatic multi-provider failover."""
    response = llm.invoke(
        [
            SystemMessage(content=system),
            HumanMessage(content=prompt),
        ]
    )
    content = response.content if hasattr(response, "content") else str(response)
    return content.strip() if isinstance(content, str) else str(content)


def _llm_fast_text(system: str, prompt: str) -> str:
    """Invoke Fast Distributed LLM for low-latency tasks (guardrails & routing)."""
    response = _fast_llm.invoke(
        [
            SystemMessage(content=system),
            HumanMessage(content=prompt),
        ]
    )
    content = response.content if hasattr(response, "content") else str(response)
    return content.strip() if isinstance(content, str) else str(content)


def run_async(coro):
    """Safely execute an async coroutine across sync and async contexts (Streamlit, CLI, worker threads)."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)


def _json_from_llm(text: str, default: dict = None) -> dict:
    print("\n========== RAW LLM RESPONSE ==========")
    print(text)
    print("======================================\n")

    cleaned = text.strip()
    # Strip markdown code fences if present (e.g. ```json ... ```)
    if "```" in cleaned:
        first_fence = cleaned.find("```")
        newline_after = cleaned.find("\n", first_fence)
        if newline_after != -1:
            rest = cleaned[newline_after + 1:]
            last_fence = rest.rfind("```")
            cleaned = rest[:last_fence].strip() if last_fence != -1 else rest.strip()

    try:
        start = cleaned.index("{")
        end = cleaned.rindex("}") + 1
        json_text = cleaned[start:end]

        print("\n========== EXTRACTED JSON ==========")
        print(json_text)
        print("====================================\n")

        return json.loads(json_text)
    except Exception as e:
        print(f"\n[WARNING] Failed to parse JSON from LLM: {e}")
        if default is not None:
            return default
        return {}


# ── Layer 1: Security & PII Scanning (Optimized Precompiled Regex & Luhn) ───
JAILBREAK_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions?",
    r"disregard\s+(all\s+)?(previous|prior)",
    r"system\s+prompt",
    r"you\s+are\s+now\s+(unfiltered|dan|developer\s+mode|jailbroken)",
    r"reveal\s+(your\s+)?(prompt|instructions?|system\s+message)",
    r"print\s+(your\s+)?(source\s+code|config|env)",
    r"what\s+is\s+your\s+system\s+prompt",
    r"<script.*?>.*?</script>",
    r"javascript:\s*",
    r"eval\(",
]

PII_PATTERNS = {
    "credit_card": r"\b(?:\d[ -]*?){13,19}\b",
    "passport": r"\b[A-PR-WY][1-9]\d\s?\d{4}[1-9]\b",
    "secret_token": r"(?:GROQ_API_KEY|NEON|DATABASE_URL|sk-lf-[a-zA-Z0-9_-]{15,}|lsv2_pt_[a-zA-Z0-9_-]{15,})",
}

# Precompile regexes once at module load for O(1) matching overhead
COMPILED_JAILBREAK_PATTERNS = [re.compile(p, re.IGNORECASE) for p in JAILBREAK_PATTERNS]
COMPILED_PII_PATTERNS = {k: re.compile(v, re.IGNORECASE) for k, v in PII_PATTERNS.items()}
OUTPUT_REDACT_PATTERN = re.compile(r"(?:sk-lf-[a-zA-Z0-9_-]{15,}|lsv2_pt_[a-zA-Z0-9_-]{15,}|postgresql:\/\/[^\s@]+@[^\s\/]+)", re.IGNORECASE)


def _is_luhn_valid(num_str: str) -> bool:
    """Validate potential credit card number using standard Luhn algorithm (mod 10)."""
    digits = [int(c) for c in num_str if c.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    reverse_digits = digits[::-1]
    for i, d in enumerate(reverse_digits):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


def sanitize_output(text: str) -> str:
    """Zero-leak output guardrail: redacts potential API keys, database connection strings, or system tokens."""
    if not text or not isinstance(text, str):
        return text
    return OUTPUT_REDACT_PATTERN.sub("[REDACTED_SECRET]", text)


def scan_security(text: str) -> tuple[bool, str]:
    """Zero-latency deterministic security scanner for jailbreaks, prompt injections, and PII."""
    clean = text.strip()

    # Fast check jailbreaks & system prompt attacks
    for regex in COMPILED_JAILBREAK_PATTERNS:
        if regex.search(clean):
            return False, "Adversarial or system prompt injection attempt detected."

    # Check sensitive PII & credentials
    for pii_type, regex in COMPILED_PII_PATTERNS.items():
        match = regex.search(clean)
        if match:
            if pii_type == "credit_card":
                matched_val = match.group(0)
                # Verify genuine credit card via Luhn algorithm to prevent false positives on random digits
                if _is_luhn_valid(matched_val):
                    return False, "Credit card or financial payment numbers detected. For your safety, do not share private payment credentials."
            elif pii_type == "secret_token":
                return False, "Probing for internal system secrets, credentials, or API keys detected."
            else:
                return False, f"Sensitive personal credentials ({pii_type}) detected. Please remove private identifiers."

    return True, ""


# ── Layer 2: Intent-Aware Supervisor Agent ────────────────────────────────────
def supervisor_agent(state: TravelState):
    query = state["user_query"].strip()

    # 1. Layer 1 Security & PII Scan (Deterministic)
    is_safe, sec_reason = scan_security(query)
    if not is_safe:
        refusal_msg = f"""⚠️ **Security Notice**: I cannot process this request.
**Reason:** {sec_reason}

**SagaTraveller** is an intelligent travel concierge. How can I assist with your journey today?
Here are examples of what you can ask:
- *Plan a 4-day budget trip to Tokyo, Japan.*
- *What travel documents do I need for abroad travel?*
- *I forgot my blanket on a winter night, what should I do?*
- *I'm feeling sick while hiking, what should I do?*
- *How to hike for beginners?*
"""
        return {
            "intent": "blocked",
            "is_valid": False,
            "response_type": "chat",
            "selected_agents": [],
            "trip_constraints": {},
            "supervisor_reasoning": sec_reason,
            "direct_response": refusal_msg,
            "final_response": refusal_msg,
            "messages": [AIMessage(content=f"Security guardrail blocked request: {sec_reason}")],
            "llm_calls": state.get("llm_calls", 0) + 1,
        }

    # 2. Fast Intent Classification & Selective Routing via _fast_llm
    classifier_prompt = f"""You are the intelligent intent classifier for SagaTraveller, a real-time AI travel concierge.
Analyze the user query and classify its intent into EXACTLY ONE of the following categories:

CATEGORIES:
1. "greeting": Casual greetings or short conversational pleasantries (e.g., "hi", "hello", "hey", "good morning", "sup").
2. "capability_help": Asking what the assistant does or how it can help (e.g., "how will u help me", "what can you do", "help me", "who are you").
3. "in_trip_situational": Real-world travel situations, mishaps, or logistical advice while on a trip (e.g., "I forgot to bring blanket it's winter night", "lost baggage at airport", "missed connecting train", "hotel room is noisy").
4. "health_safety_emergency": In-trip medical, outdoor physical distress, or safety advice (e.g., "I am feeling sick while hiking", "altitude sickness symptoms", "stung by a jellyfish", "food poisoning abroad").
5. "activity_how_to": General travel FAQs, document requirements, packing, or activity how-to guides (e.g., "how to to hike", "what doc needed for abroad travel", "how to take the Tokyo metro", "tipping etiquette in Europe").
6. "trip_planning": User wants an itinerary, vacation schedule, or flight/hotel planning for a specific destination (e.g., "Plan a 4-day trip to Tokyo", "3-day luxury weekend in Paris", "budget vacation to Dubai").

Return strict JSON only (no markdown, no backticks):
{{
  "intent": "greeting | capability_help | in_trip_situational | health_safety_emergency | activity_how_to | trip_planning",
  "reasoning": "brief explanation"
}}

User query:
{query}
"""

    raw_classification = _llm_fast_text(
        "You are a strict JSON classifier. Classify user intent accurately.",
        classifier_prompt,
    )
    parsed_class = _json_from_llm(raw_classification, default={"intent": "trip_planning", "reasoning": "Default fallback"})
    intent = parsed_class.get("intent", "trip_planning")

    print(f"\n[SUPERVISOR] Classified Intent: {intent} (Query: '{query}')\n")

    # 3. Direct Fast-Path Handlers for Non-Planning Intents (< 1.5s latency)
    if intent in ("greeting", "capability_help", "in_trip_situational", "health_safety_emergency", "activity_how_to"):
        direct_prompt = f"""You are SagaTraveller, an empathetic, highly knowledgeable, and practical AI Travel Concierge.
Provide an immediate, well-structured, and helpful response to the user's query according to its category:

Category: {intent}
User Query: "{query}"

GUIDELINES BY CATEGORY:
- If "greeting": Warm, friendly greeting. Introduce yourself as SagaTraveller and invite the user to plan a trip, search flights/hotels, or ask any travel advisory question. Mention 3 popular destinations (e.g. Tokyo, Paris, Dubai).
- If "capability_help": Provide a clear, bulleted breakdown of your 4 key superpowers: (1) Custom Day-by-Day Itineraries, (2) Live Flight & Hotel Research, (3) Smart Budget Optimization in any currency, and (4) In-Trip Real-Time Advisory & Outdoor Guides.
- If "in_trip_situational" (e.g. forgot blanket on winter night): Empathize immediately! Give practical, actionable warming and insulation steps: (1) Layering clothing, jackets, beanies & socks, (2) Contacting hotel reception/host for spare heaters or duvets, (3) Makeshift insulation using clean dry towels/coats, (4) Finding nearby 24/7 convenience stores for chemical heat packs (kairo) or emergency foil blankets, (5) Drinking warm water.
- If "health_safety_emergency" (e.g. feeling sick while hiking): Put safety first! Give structured first-aid guidance: (1) Stop ascending immediately and sit down in shade/shelter, (2) Hydrate slowly and take an electrolyte snack, (3) Check for Altitude Sickness (nausea, headache, dizziness above 2500m -> mandatory descent), Heat Exhaustion, or Hypothermia, (4) When to seek emergency rescue (call 911/112 or local park rangers if chest pain, confusion, or severe symptoms occur).
- If "activity_how_to" (e.g. "how to hike" or "what doc needed for abroad travel"): Give an expert, actionable checklist with practical tips and best practices.

Use clean markdown with bullet points and bold headers. Do NOT generate flight or hotel tables or fake daily schedules for non-planning queries!
"""
        direct_response = _llm_fast_text(
            "You are SagaTraveller, the personal AI travel concierge. Answer directly with practical expertise.",
            direct_prompt,
        )
        direct_response = sanitize_output(direct_response)

        return {
            "intent": intent,
            "is_valid": True,
            "response_type": "chat",
            "selected_agents": [],
            "trip_constraints": {},
            "supervisor_reasoning": f"Handled directly via concierge advisory ({intent}).",
            "direct_response": direct_response,
            "final_response": direct_response,
            "messages": [AIMessage(content=direct_response)],
            "llm_calls": state.get("llm_calls", 0) + 2,
        }

    # 4. Multi-Agent Trip Planning Path (On-Demand Agent Triggering)
    planning_prompt = f"""You are the supervisor of a real-world multi-agent travel planning system.
The user wants to plan a trip or travel itinerary.

Determine trip constraints and select ONLY the specialist agents actually needed:
Available agents:
- flight_agent: Select ONLY if user mentions flights, airlines, airport routes, or needs airfare estimates.
- hotel_agent: Select ONLY if user needs hotel, resort, neighborhood, or lodging recommendations.
- weather_agent: Select ONLY if weather forecast, seasonal climate, or packing tips are helpful.
- budget_agent: Select ONLY if budget, price, costs, or affordability are discussed.
- itinerary_agent: Required to structure the day-by-day travel plan.

Return strict JSON only:
{{
  "selected_agents": ["flight_agent", "hotel_agent", "weather_agent", "budget_agent", "itinerary_agent"],
  "trip_constraints": {{
    "destination": "",
    "origin": "",
    "duration": "",
    "budget": "",
    "travel_style": "",
    "special_preferences": []
  }},
  "reasoning": "why these agents were selected"
}}

User request:
{query}
"""

    raw_plan = _llm_fast_text(
        "You route work to specialist agents. Return strict JSON only.",
        planning_prompt,
    )

    default_routing = {
        "selected_agents": ["flight_agent", "hotel_agent", "weather_agent", "budget_agent", "itinerary_agent"],
        "trip_constraints": {
            "destination": query,
            "origin": "",
            "duration": "3 days",
            "budget": "Flexible",
            "travel_style": "Comfortable",
            "special_preferences": []
        },
        "reasoning": "Comprehensive multi-agent travel plan."
    }

    parsed = _json_from_llm(raw_plan, default=default_routing)
    selected = parsed.get("selected_agents") or default_routing["selected_agents"]
    trip_constraints = parsed.get("trip_constraints") or default_routing["trip_constraints"]
    reasoning = parsed.get("reasoning", "")

    return {
        "intent": "trip_planning",
        "is_valid": True,
        "response_type": "itinerary",
        "selected_agents": selected,
        "trip_constraints": trip_constraints,
        "supervisor_reasoning": reasoning,
        "messages": [AIMessage(content="Supervisor planned agent execution.")],
        "llm_calls": state.get("llm_calls", 0) + 2,
    }


def direct_response_agent(state: TravelState):
    """Outputs the direct response for greetings, advisory, health, or security."""
    resp = state.get("direct_response") or state.get("final_response") or "How can I assist your travels today?"
    sanitized = sanitize_output(resp)
    return {
        "final_response": sanitized,
        "messages": [AIMessage(content=sanitized)],
    }






# without guardrail

# def supervisor_agent(state: TravelState):
#     query = state["user_query"]
#     prompt = f"""
# You are the supervisor of a real-world multi-agent travel planning system.

# Decide which specialist agents are needed for this user request.

# Available agents:
# - flight_agent: use when flights, airports, airlines, routes, or airfare guidance are needed
# - hotel_agent: use when hotels, stays, neighborhoods, or accommodation are needed
# - weather_agent: use when weather, climate, season, packing, or forecast is useful
# - budget_agent: use when budget, affordability, cost, or price constraints are mentioned
# - itinerary_agent: almost always needed to produce the travel plan

# Return only JSON with this schema:
# {{
#   "selected_agents": ["flight_agent", "hotel_agent", "weather_agent", "budget_agent", "itinerary_agent"],
#   "trip_constraints": {{
#     "destination": "",
#     "origin": "",
#     "duration": "",
#     "budget": "",
#     "travel_style": "",
#     "special_preferences": []
#   }},
#   "reasoning": ""
# }}

# User request:
# {query}
# """
    
#     raw = _llm_text(
#         "You route work to specialist agents. Return strict JSON only.",
#         prompt,
#     )

#     print("\n========== RAW LLM RESPONSE ==========")
#     print(raw)
#     print("======================================\n")

#     parsed = _json_from_llm(raw)
#     print("\n========== PARSED JSON ==========")
#     print(json.dumps(parsed, indent=2))
#     print("=================================\n")

#     print(type(raw))
#     print(type(parsed))

#     selected = parsed["selected_agents"]       

#     return {
#         "selected_agents": selected,
#         "trip_constraints": parsed["trip_constraints"],
#         "supervisor_reasoning": parsed["reasoning"],
#         "messages": [AIMessage(content="Supervisor created the agent plan.")],
#         "llm_calls": state.get("llm_calls", 0) + 1,
#     }



async def _fetch_flight_data(destination: str):
    """Fetch airports and airlines concurrently via asyncio.gather."""
    airports_task = list_airports(destination, limit=10)
    airlines_task = list_airlines("", limit=10)
    airports_res, airlines_res = await asyncio.gather(
        airports_task, airlines_task, return_exceptions=True
    )
    airports = airports_res if not isinstance(airports_res, Exception) else f"Error: {airports_res}"
    airlines = airlines_res if not isinstance(airlines_res, Exception) else f"Error: {airlines_res}"
    return airports, airlines


async def _fetch_weather_data(city: str):
    """Fetch current weather and forecast concurrently via asyncio.gather."""
    curr_task = current_weather(city)
    fc_task = forecast(city)
    curr_res, fc_res = await asyncio.gather(
        curr_task, fc_task, return_exceptions=True
    )
    weather_data = curr_res if not isinstance(curr_res, Exception) else f"Error: {curr_res}"
    forecast_data = fc_res if not isinstance(fc_res, Exception) else f"Error: {fc_res}"
    return weather_data, forecast_data


async def _run_flight_agent_async(state: TravelState) -> dict:
    query = state["user_query"]
    constraints = state.get("trip_constraints", {})
    destination = constraints.get("destination", "")

    print("\n========== [PARALLEL] FLIGHT AGENT START ==========")
    print("Query:", query)
    print("Constraints:", constraints)
    print("===================================================\n")

    airports, airlines = await _fetch_flight_data(destination)

    print("\n========== AIRPORT MCP DATA ==========")
    print(airports)
    print("======================================\n")

    print("\n========== AIRLINE MCP DATA ==========")
    print(airlines)
    print("======================================\n")

    prompt = f"""
Create flight guidance for this trip.

User request:
{query}

Trip constraints:
{constraints}

Airport MCP data:
{str(airports)[:3000]}

Airline MCP data:
{str(airlines)[:3000]}

Include likely departure/arrival airports, relevant airlines,
estimated duration, fare range (default to USD $ unless user specified another currency),
peak season warning, and booking advice.
"""

    result = await asyncio.to_thread(_llm_text, "You are a flight planning specialist.", prompt)

    print("\n========== [PARALLEL] FLIGHT AGENT OUTPUT ==========")
    print(result)
    print("====================================================\n")

    return {
        "flight_results": result,
        "messages": [AIMessage(content="Flight agent completed.")],
        "llm_calls": 1,
    }


async def _run_hotel_agent_async(state: TravelState) -> dict:
    query = f"Best hotels and areas to stay for: {state['user_query']}"

    print("\n========== [PARALLEL] HOTEL AGENT START ==========")
    print(query)
    print("==================================================\n")

    try:
        result = await tavily_search(query)
    except Exception as e:
        print(f"[HOTEL AGENT ERROR] {e}")
        result = f"Hotel recommendations based on query '{query}' unavailable: {e}"

    print("\n========== [PARALLEL] HOTEL SEARCH RESULT ==========")
    print(result)
    print("====================================================\n")

    return {
        "hotel_results": str(result),
        "messages": [AIMessage(content="Hotel agent completed.")],
    }


async def _run_weather_agent_async(state: TravelState) -> dict:
    constraints = state.get("trip_constraints", {})
    city = constraints.get("destination", "")

    print("\n========== [PARALLEL] WEATHER AGENT START ==========")
    print("City:", city)
    print("====================================================\n")

    weather_data, forecast_data = await _fetch_weather_data(city)

    print("\n========== CURRENT WEATHER ==========")
    print(weather_data)
    print("=====================================\n")

    print("\n========== WEATHER FORECAST ==========")
    print(forecast_data)
    print("======================================\n")

    result = f"""
Current weather:
{weather_data}

Forecast:
{forecast_data}
"""

    print("\n========== [PARALLEL] WEATHER AGENT OUTPUT ==========")
    print(result)
    print("=====================================================\n")

    return {
        "weather_results": result,
        "messages": [AIMessage(content="Weather agent completed.")],
    }


def parallel_specialists(state: TravelState) -> dict:
    """
    Executes flight_agent, hotel_agent, and weather_agent concurrently via asyncio.gather.
    Cuts ~110 seconds off sequential graph time by overlapping MCP data fetching and LLM reasoning.
    """
    selected = state.get("selected_agents") or []
    target_agents = [a for a in ["flight_agent", "hotel_agent", "weather_agent"] if not selected or a in selected]
    print(f"\n=======================================================")
    print(f"🚀 [PARALLEL SPECIALISTS] Concurrently launching {len(target_agents)} agents: {target_agents}")
    print(f"=======================================================\n")

    async def _gather_specialists():
        coros = []
        names = []

        if not selected or "flight_agent" in selected:
            coros.append(_run_flight_agent_async(state))
            names.append("flight_agent")
        if not selected or "hotel_agent" in selected:
            coros.append(_run_hotel_agent_async(state))
            names.append("hotel_agent")
        if not selected or "weather_agent" in selected:
            coros.append(_run_weather_agent_async(state))
            names.append("weather_agent")

        if not coros:
            return {}

        results = await asyncio.gather(*coros, return_exceptions=True)

        combined = {}
        llm_count = 0
        all_messages = []

        for name, res in zip(names, results):
            if isinstance(res, Exception):
                print(f"[PARALLEL SPECIALIST EXCEPTION in {name}]: {res}")
                if name == "flight_agent":
                    combined["flight_results"] = f"Flight details unavailable: {res}"
                elif name == "hotel_agent":
                    combined["hotel_results"] = f"Hotel recommendations unavailable: {res}"
                elif name == "weather_agent":
                    combined["weather_results"] = f"Weather forecast unavailable: {res}"
            elif isinstance(res, dict):
                for k, v in res.items():
                    if k == "messages":
                        all_messages.extend(v)
                    elif k == "llm_calls":
                        llm_count += v
                    else:
                        combined[k] = v

        if all_messages:
            combined["messages"] = all_messages
        combined["llm_calls"] = state.get("llm_calls", 0) + llm_count
        return combined

    return run_async(_gather_specialists())


def flight_agent(state: TravelState):
    """Direct synchronous runner for flight_agent (for backward compatibility)."""
    return run_async(_run_flight_agent_async(state))


def hotel_agent(state: TravelState):
    """Direct synchronous runner for hotel_agent (for backward compatibility)."""
    return run_async(_run_hotel_agent_async(state))


def weather_agent(state: TravelState):
    """Direct synchronous runner for weather_agent (for backward compatibility)."""
    return run_async(_run_weather_agent_async(state))



def budget_agent(state: TravelState):

    print("\n========== BUDGET AGENT INPUT ==========")
    print("Trip Constraints:")
    print(state.get("trip_constraints"))
    print("\nFlight Results:")
    print(state.get("flight_results"))
    print("\nHotel Results:")
    print(state.get("hotel_results"))
    print("\nWeather Results:")
    print(state.get("weather_results"))
    print("=========================================\n")

    prompt = f"""
Analyze whether this trip plan is realistic for the user's budget.

User request:
{state['user_query']}

Constraints:
{state.get('trip_constraints', {})}

Flight results:
{state.get('flight_results', '')}

Hotel results:
{state.get('hotel_results', '')}

Weather results:
{state.get('weather_results', '')}

Return a concise budget assessment with:
1. estimated cost categories (in USD $ by default, or the currency requested by the user)
2. risk areas
3. money-saving suggestions
4. whether the plan seems feasible
"""

    result = _llm_text(
        "You are a practical travel budget analyst. Default to USD ($) unless the user specifically requested another currency.",
        prompt,
    )

    print("\n========== BUDGET AGENT OUTPUT ==========")
    print(result)
    print("=========================================\n")

    return {
        "budget_results": result,
        "messages": [AIMessage(content="Budget agent completed.")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }



def _is_vague_or_affirming_feedback(feedback_text: str) -> bool:
    if not feedback_text:
        return True
    
    clean_fb = feedback_text.strip().lower().strip("!.,;:-_")
    if not clean_fb:
        return True

    vague_phrases = {
        "ok", "okay", "k", "kk", "good", "fine", "looks good", "look good", 
        "yes", "yeah", "yep", "cool", "nice", "great", "perfect", "sure", 
        "no changes", "no change", "keep it", "same", "alright", "all good", 
        "thanks", "thank you", "proceed", "continue", "done", "no", "none"
    }

    if clean_fb in vague_phrases:
        return True

    revision_action_words = {
        "add", "remove", "delete", "change", "only", "instead", "less", "more", 
        "don't", "keep", "update", "replace", "reduce", "increase", "budget", 
        "hotel", "flight", "day", "night", "cost", "expensive", "cheaper", 
        "visit", "see", "trip", "extend", "shorten", "avoid", "include", "exclude"
    }

    words = set(clean_fb.split())
    if len(clean_fb) < 25 and not words.intersection(revision_action_words):
        return True

    return False


def itinerary_agent(state: TravelState):

    print("\n========== ITINERARY AGENT INPUT ==========")
    print("Trip Constraints:")
    print(state.get("trip_constraints"))

    print("\nFlight Results:")
    print(state.get("flight_results"))

    print("\nHotel Results:")
    print(state.get("hotel_results"))

    print("\nWeather Results:")
    print(state.get("weather_results"))

    print("\nBudget Results:")
    print(state.get("budget_results"))

    print("\nHuman Feedback (Revision):")
    print(state.get("human_feedback"))
    print("===========================================\n")

    current_draft = state.get("itinerary", "")
    human_fb = state.get("human_feedback", "")

    DAY_FORMAT_INSTRUCTIONS = """
MANDATORY DOCUMENT STRUCTURE & FORMAT RULES:

1. FLIGHT OPTIONS SECTION:
You MUST provide a complete markdown table of flight choices:
| Airline | Route | Departure | Arrival | Duration | Est. Price |
|---------|-------|-----------|---------|----------|------------|
Followed by short booking advice.

2. HOTEL RECOMMENDATIONS SECTION:
You MUST provide a complete markdown table of hotel choices:
| Hotel Name | Neighborhood | Rating | Price / Night | Total Stay |
|------------|--------------|--------|---------------|------------|
Followed by short neighborhood advice.

3. WEATHER FORECAST SECTION:
You MUST provide a complete markdown table for the trip forecast:
| Day / Date | Condition | High Temp | Low Temp | Advice / Humidity |
|------------|-----------|-----------|----------|-------------------|
Followed by packing tips.

4. DAY-BY-DAY ITINERARY SCHEDULE (MANDATORY TEXT FORMAT — NO TABLES FOR DAILY SCHEDULE):
For each day of the trip, use this EXACT structure:

## Day N — [Theme Title]
**Location:** [Specific area/neighborhood, City]

### Morning
- **Activity:** [Specific activity name]
- **Details:** [What to do, opening hours, entry fee if any]
- **Budget:** $[amount]

### Afternoon
- **Activity:** [Specific activity name]
- **Details:** [What to do, distance, travel time]
- **Budget:** $[amount]

### Evening
- **Activity:** [Specific activity name]
- **Details:** [Restaurant name or experience details]
- **Budget:** $[amount]

**Day N Total:** $[sum of day budget]

---

5. OVERALL BUDGET SUMMARY SECTION:
You MUST provide a complete markdown table categorizing all expenses:
| Category | Estimated Cost |
|----------|---------------|
| Flights | $[amount] |
| Accommodation | $[amount] |
| Daily Activities & Sightseeing | $[amount] |
| Food & Dining | $[amount] |
| Local Transport | $[amount] |
| Miscellaneous | $[amount] |
| **Total Estimated Cost** | **$[total]** |

6. PRACTICAL TIPS & BOOKING CHECKLIST:
Provide 4-5 actionable tips and a numbered booking checklist.
"""


    # If there is an existing draft itinerary in state, use it as the PRIMARY GROUND TRUTH
    if current_draft and human_fb and not state.get("approved", False) and not _is_vague_or_affirming_feedback(human_fb):
        prompt = f"""
You are an expert travel planner revising an existing travel itinerary based on user instructions.

PRIMARY GROUND TRUTH (CURRENT DRAFT ITINERARY TO MODIFY):
{current_draft}

USER REVISION INSTRUCTIONS (HIGHEST PRIORITY):
"{human_fb}"

STRICT REVISION & SYNCHRONIZATION RULES:
1. BASELINE DOCUMENT: Treat the CURRENT DRAFT ITINERARY above as your absolute ground truth baseline. Apply the user's revision instructions directly to this baseline.
2. DO NOT REVERT: Do NOT revert to any earlier trip duration, number of days, or outdated items from initial queries unless the user explicitly asks you to.
3. COMPLETE METADATA SYNCHRONIZATION: You MUST ensure EVERY section of the updated document is 100% mutually consistent:
   - TITLE: Reflect the exact revised trip duration and destination (e.g. "1-Day Cultural Trip to Bangkok" if reduced to 1 day).
   - OVERVIEW: State the updated duration accurately.
   - ITINERARY SCHEDULE: Include ONLY the active/requested days — formatted as rich text per day, NOT as a table.
   - TOTAL ESTIMATED COST: Recalculate total costs ONLY for the revised duration and included days.
4. META-QUESTIONS & AMBIGUOUS FEEDBACK: If the user feedback asks a question, mentions past prompts, or does NOT specify concrete structural changes (such as adding/removing days or changing budget), PRESERVE the CURRENT DRAFT ITINERARY cleanly without inserting meta-conversational text into the travel schedule body.
5. NO META-EXPLANATIONS OR SELF-CHECK LISTS:
   - Output ONLY the complete, ready-to-use travel itinerary document.
   - NEVER output internal reasoning, validation checklists, or sections explaining "How the elements stay consistent" or "Why these rules are satisfied".
   - You MUST include the full day-by-day activities schedule with concrete Morning, Afternoon, and Evening details for every single day.

{DAY_FORMAT_INSTRUCTIONS}
"""
    else:
        # Initial draft itinerary creation from scratch (or fallback)
        prompt = f"""
Create a clear draft travel itinerary.

User request:
{state['user_query']}

Trip constraints:
{state.get('trip_constraints', {})}

Flight results:
{state.get('flight_results', '')}

Hotel results:
{state.get('hotel_results', '')}

Weather results:
{state.get('weather_results', '')}

Budget results:
{state.get('budget_results', '')}

Make the output structured, practical, and ready for human review.
Format all estimated costs and budgets in USD ($) by default, or the currency specifically requested by the user.
Ensure title, overview duration, daily schedule, and total estimated cost calculation are ALL 100% consistent with each other.
CRITICAL: Output ONLY the complete travel plan itself with full daily schedule and tables. Never output meta-reasoning, validation checklists, or commentary explaining your thought process.

{DAY_FORMAT_INSTRUCTIONS}
"""

    result = _llm_text(
        "You are an expert itinerary planner. Ensure title, overview, schedule, and budget estimations are 100% consistent.",
        prompt,
    )

    print("\n========== ITINERARY OUTPUT ==========")
    print(result)
    print("======================================\n")

    sanitized_result = sanitize_output(result)

    approval_request = f"""
Please review this draft travel plan.

{sanitized_result}

Reply with approval or feedback.
"""

    return {
        "itinerary": sanitized_result,
        "approval_request": approval_request,
        "messages": [AIMessage(content="Draft itinerary created for human review.")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }


def human_approval_agent(state: TravelState):
    feedback = interrupt(
        {
            "question": "Do you approve this itinerary?",
            "draft_itinerary": state.get("itinerary", ""),
            "approval_request": state.get("approval_request", ""),
            "expected_response": {
                "approved": True,
                "feedback": "Optional feedback for revision",
            },
        }
    )

    approved = feedback["approved"]
    human_feedback = feedback.get("feedback", "")

    # Safety check: If user selected 'No, revise' but provided no actionable feedback (e.g., 'ok', 'looks good'),
    # treat it as approval of the current draft itinerary rather than triggering a flawed revision loop.
    if not approved and _is_vague_or_affirming_feedback(human_feedback):
        print(f"\n[human_approval_agent] Normalizing vague feedback '{human_feedback}' to approved=True")
        approved = True

    return {
        "approved": approved,
        "human_feedback": human_feedback,
        "messages": [AIMessage(content="Human approval step completed.")],
    }



def final_response_agent(state: TravelState):

    print("\n========== FINAL AGENT INPUT ==========")
    print("Approved:", state.get("approved"))
    print("Feedback:", state.get("human_feedback"))
    print("=======================================\n")

    # The user reviewed and approved state['itinerary'].
    # To guarantee zero loss of detail, tables, descriptions, or day-by-day schedules,
    # the approved itinerary is preserved 100% in full as the final publication plan.
    approved_itinerary = state.get("itinerary", "")
    sanitized = sanitize_output(approved_itinerary)

    print("\n========== FINAL RESPONSE (FULL APPROVED ITINERARY) ==========")
    print(sanitized[:500] + ("..." if len(sanitized) > 500 else ""))
    print("===============================================================\n")

    return {
        "final_response": sanitized,
        "messages": [AIMessage(content=sanitized)],
        "llm_calls": state.get("llm_calls", 0),
    }