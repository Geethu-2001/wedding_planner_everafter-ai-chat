# from typing import TypedDict
# from langgraph.graph import StateGraph, START, END
# from langchain_ollama import ChatOllama
# from wedding_planner.config import settings
# from wedding_planner.integrations.tavily import search_web


# class State(TypedDict, total=False):
#     request: str
#     location: str
#     category: str
#     budget_summary: dict
#     route_venue: bool
#     route_vendor: bool
#     venue_results: list[dict]
#     vendor_results: list[dict]
#     plan: str
#     errors: list[str]


# def supervisor(state):
#     query = state.get("request", "").lower()
#     return {
#         "route_venue": state.get("category", "").lower() in {"venue", "wedding venue"}
#                       or any(word in query for word in ("venue", "hall", "resort")),
#         "route_vendor": (
#             bool(state.get("category"))
#             and state.get("category", "").lower() not in {"venue", "wedding venue"}
#         ) or any(word in query for word in ("photograph", "cater", "decor", "makeup", "vendor", "dj")),
#     }


# def venue_research(state):
#     try:
#         results = search_web(
#             f"wedding venues halls resorts {state.get('request', '')}",
#             state.get("location", "India"),
#         )
#         return {"venue_results": results}
#     except Exception as exc:
#         return {"errors": state.get("errors", []) + [f"Venue research failed: {exc}"]}


# def vendor_research(state):
#     try:
#         category = state.get("category") or state.get("request", "wedding vendors")
#         results = search_web(
#             f"{category} wedding services packages reviews {state.get('request', '')}",
#             state.get("location", "India"),
#         )
#         return {"vendor_results": results}
#     except Exception as exc:
#         return {"errors": state.get("errors", []) + [f"Vendor research failed: {exc}"]}


# def budget_advisor(state):
#     try:
#         prompt = (
#             "Give practical wedding-budget trade-off advice. Do not calculate or change figures. "
#             f"Request: {state.get('request')}. Python-calculated budget: {state.get('budget_summary', {})}"
#         )
#         answer = ChatOllama(
#             model=settings.ollama_model,
#             base_url=settings.ollama_base_url,
#             temperature=settings.ollama_temperature,
#         ).invoke(prompt).content
#         return {"plan": str(answer)}
#     except Exception as exc:
#         return {"plan": "Budget advice unavailable. Check that Ollama is running and the model is installed.",
#                 "errors": state.get("errors", []) + [str(exc)]}


# def coordinator(state):
#     guidance = (
#         "Coordinator checks: confirm date availability directly with the provider, obtain a written "
#         "quotation, check inclusions/exclusions, cancellation terms, taxes, travel costs and payment milestones."
#     )
#     return {"plan": (state.get("plan", "") + "\\n\\n" + guidance).strip()}


# def build_graph():
#     graph = StateGraph(State)
#     # Exactly five agents: supervisor, venue research, vendor research, budget advisor, coordinator.
#     for name, node in [
#         ("supervisor", supervisor),
#         ("venue_research", venue_research),
#         ("vendor_research", vendor_research),
#         ("budget_advisor", budget_advisor),
#         ("coordinator", coordinator),
#     ]:
#         graph.add_node(name, node)
#     graph.add_edge(START, "supervisor")

#     def route(state):
#         targets = []
#         if state.get("route_venue"):
#             targets.append("venue_research")
#         if state.get("route_vendor"):
#             targets.append("vendor_research")
#         return targets or ["budget_advisor"]

#     graph.add_conditional_edges(
#         "supervisor", route,
#         {"venue_research": "venue_research", "vendor_research": "vendor_research",
#          "budget_advisor": "budget_advisor"},
#     )
#     graph.add_edge("venue_research", "budget_advisor")
#     graph.add_edge("vendor_research", "budget_advisor")
#     graph.add_edge("budget_advisor", "coordinator")
#     graph.add_edge("coordinator", END)
#     return graph.compile()


# def run_planning(request, location, budget_summary=None, category=None):
#     return build_graph().invoke(
#         {"request": request, "location": location, "category": category or "",
#          "budget_summary": budget_summary or {}},
#         config={"recursion_limit": 16},
#     )


# def research_category(category, requirements, location, budget_summary=None):
#     return run_planning(
#         request=requirements or f"Find {category} providers",
#         location=location,
#         budget_summary=budget_summary,
#         category=category,
#     )


from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from langchain_ollama import ChatOllama

from wedding_planner.config import settings
from wedding_planner.integrations.tavily import search_web


class State(TypedDict, total=False):
    request: str
    location: str
    category: str
    budget_summary: dict
    route_venue: bool
    route_vendor: bool
    venue_results: list[dict]
    vendor_results: list[dict]
    plan: str
    errors: list[str]


def supervisor(state):
    query = state.get("request", "").lower()
    category = state.get("category", "").lower()

    return {
        "route_venue": (
            category in {"venue", "wedding venue"}
            or any(word in query for word in ("venue", "hall", "resort"))
        ),
        "route_vendor": (
            bool(category) and category not in {"venue", "wedding venue"}
        ) or any(
            word in query
            for word in (
                "photograph", "cater", "decor",
                "makeup", "vendor", "dj"
            )
        ),
    }


def venue_research(state):
    try:
        results = search_web(
            f"wedding venues halls resorts {state.get('request', '')}",
            state.get("location", "India"),
        )
        return {"venue_results": results}

    except Exception as exc:
        errors = list(state.get("errors", []))
        errors.append(f"Venue research failed: {exc}")
        return {"errors": errors}


def vendor_research(state):
    try:
        category = state.get("category") or state.get(
            "request", "wedding vendors"
        )

        results = search_web(
            f"{category} wedding services packages reviews "
            f"{state.get('request', '')}",
            state.get("location", "India"),
        )

        return {"vendor_results": results}

    except Exception as exc:
        errors = list(state.get("errors", []))
        errors.append(f"Vendor research failed: {exc}")
        return {"errors": errors}


def budget_advisor(state):
    try:
        summary = state.get("budget_summary") or {}

        prompt = f"""
You are the Budget Advisor Agent for an Indian wedding planning application.

Analyze the following Python-calculated wedding budget information.

User request:
{state.get("request", "")}

Wedding budget information:
{summary}

Your responsibilities:

1. Explain the total wedding budget.
2. Explain how much money is already committed.
3. Explain how much money remains.
4. Identify whether the wedding is over budget.
5. Review the suggested category allocations.
6. Identify categories where the couple should control spending.
7. Suggest practical ways to reduce wedding costs.
8. Explain whether additional vendor bookings are affordable.

Important rules:
- Use only the figures supplied in the budget information.
- Never invent expenses, quotations, vendor prices, or savings.
- Never recalculate or modify the Python-calculated figures.
- If information is missing, clearly say that it is unavailable.
- Give practical recommendations suitable for Indian weddings.
- Keep the advice clear and easy to understand.

Format your answer with these headings:

### Budget Overview
### Spending Risks
### Category Recommendations
### Ways to Save Money
### Next Steps
"""

        response = ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=settings.ollama_temperature,
        ).invoke(prompt)

        return {"plan": str(response.content)}

    except Exception as exc:
        errors = list(state.get("errors", []))
        errors.append(f"Budget Advisor failed: {exc}")

        return {
            "plan": (
                "Budget advice is currently unavailable. "
                "Please check that Ollama is running and the configured "
                "model is installed."
            ),
            "errors": errors,
        }


def coordinator(state):
    guidance = (
        "### Wedding Planning Checks\n\n"
        "- Confirm the wedding date directly with each provider.\n"
        "- Obtain a written quotation.\n"
        "- Check package inclusions and exclusions.\n"
        "- Confirm cancellation and refund terms.\n"
        "- Check taxes and additional travel costs.\n"
        "- Record payment milestones and due dates."
    )

    existing_plan = state.get("plan", "")

    return {
        "plan": f"{existing_plan}\n\n{guidance}".strip()
    }


def build_graph():
    graph = StateGraph(State)

    # Exactly five agents.
    for name, node in [
        ("supervisor", supervisor),
        ("venue_research", venue_research),
        ("vendor_research", vendor_research),
        ("budget_advisor", budget_advisor),
        ("coordinator", coordinator),
    ]:
        graph.add_node(name, node)

    graph.add_edge(START, "supervisor")

    def route(state):
        targets = []

        if state.get("route_venue"):
            targets.append("venue_research")

        if state.get("route_vendor"):
            targets.append("vendor_research")

        return targets or ["budget_advisor"]

    graph.add_conditional_edges(
        "supervisor",
        route,
        {
            "venue_research": "venue_research",
            "vendor_research": "vendor_research",
            "budget_advisor": "budget_advisor",
        },
    )

    graph.add_edge("venue_research", "budget_advisor")
    graph.add_edge("vendor_research", "budget_advisor")
    graph.add_edge("budget_advisor", "coordinator")
    graph.add_edge("coordinator", END)

    return graph.compile()


def run_planning(request, location, budget_summary=None, category=None):
    return build_graph().invoke(
        {
            "request": request,
            "location": location,
            "category": category or "",
            "budget_summary": budget_summary or {},
        },
        config={"recursion_limit": 16},
    )


def research_category(category, requirements, location, budget_summary=None):
    return run_planning(
        request=requirements or f"Find {category} providers",
        location=location,
        budget_summary=budget_summary,
        category=category,
    )

