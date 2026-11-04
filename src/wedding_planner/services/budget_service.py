# from decimal import Decimal
# from wedding_planner.models import Wedding,Expense
# from wedding_planner.repositories import require_membership
# ALLOCATIONS={"Venue":25,"Catering":20,"Photography and videography":10,"Decoration":10,
# "Outfits and styling":8,"Accommodation and transportation":7,"Makeup and mehendi":6,
# "Invitations and stationery":3,"Music and entertainment":3,"Other services":3,"Emergency reserve":5}
# def suggest_budget_allocation(total: Decimal):
#     return {k:(total*Decimal(v)/100).quantize(Decimal("0.01")) for k,v in ALLOCATIONS.items()}
# def budget_summary(session,wedding_id,user_id):
#     require_membership(session,wedding_id,user_id); wedding=session.get(Wedding,wedding_id)
#     rows=session.query(Expense).filter_by(wedding_id=wedding_id).all()
#     total=Decimal(wedding.total_budget or 0)
#     planned=sum((Decimal(x.amount) for x in rows if x.expense_type in ("planned","confirmed","actual")),Decimal(0))
#     actual=sum((Decimal(x.amount) for x in rows if x.expense_type=="actual"),Decimal(0))
#     return {"total_budget":total,"planned_expenses":planned,"actual_expenses":actual,
#             "remaining_budget":total-planned,"over_budget":planned>total}


from decimal import Decimal, ROUND_HALF_UP

from wedding_planner.models import Wedding, Expense
from wedding_planner.repositories import require_membership


ALLOCATIONS = {
    "Venue": 25,
    "Catering": 20,
    "Photography and videography": 10,
    "Decoration": 10,
    "Outfits and styling": 8,
    "Accommodation and transportation": 7,
    "Makeup and mehendi": 6,
    "Invitations and stationery": 3,
    "Music and entertainment": 3,
    "Other services": 3,
    "Emergency reserve": 5,
}

ZERO = Decimal("0.00")
CENT = Decimal("0.01")


def money(value):
    """Convert a value safely into a two-decimal-place Decimal."""
    return Decimal(str(value or 0)).quantize(
        CENT,
        rounding=ROUND_HALF_UP,
    )


def suggest_budget_allocation(total: Decimal):
    """Suggest how the total wedding budget can be divided."""
    total = money(total)

    return {
        category: money(total * Decimal(percent) / Decimal("100"))
        for category, percent in ALLOCATIONS.items()
    }


def budget_summary(session, wedding_id, user_id):
    """Calculate the wedding budget and generate practical advice."""

    # Verify that the user belongs to this wedding.
    require_membership(session, wedding_id, user_id)

    wedding = session.get(Wedding, wedding_id)

    if wedding is None:
        raise ValueError("Wedding project not found.")

    total = money(wedding.total_budget)

    expenses = (
        session.query(Expense)
        .filter_by(wedding_id=wedding_id)
        .all()
    )

    planned = ZERO
    confirmed = ZERO
    actual = ZERO

    for expense in expenses:
        amount = money(expense.amount)
        expense_type = (expense.expense_type or "").lower()

        if expense_type == "planned":
            planned += amount

        elif expense_type == "confirmed":
            confirmed += amount

        elif expense_type == "actual":
            actual += amount

    # Total money already planned, committed, or spent.
    committed = planned + confirmed + actual

    remaining = total - committed

    # Calculate budget usage percentage.
    if total > ZERO:
        usage_percentage = (
            committed / total * Decimal("100")
        ).quantize(CENT, rounding=ROUND_HALF_UP)
    else:
        usage_percentage = ZERO

    allocations = suggest_budget_allocation(total)

    # Generate advice using actual calculated figures.
    advice = []

    if total <= ZERO:
        advice.append(
            "Add your total wedding budget to receive budget recommendations."
        )

    elif remaining < ZERO:
        advice.append(
            f"Your wedding budget is exceeded by ₹{abs(remaining):,.2f}. "
            "Review planned expenses and consider reducing costs."
        )

    elif remaining == ZERO:
        advice.append(
            "Your entire wedding budget has been allocated. "
            "Avoid adding new expenses without reducing existing costs."
        )

    elif usage_percentage >= Decimal("90"):
        advice.append(
            "You have used at least 90% of your budget. "
            "Be careful before confirming additional bookings."
        )

    elif usage_percentage >= Decimal("75"):
        advice.append(
            "You have used at least 75% of your budget. "
            "Review remaining bookings and keep some money for unexpected costs."
        )

    else:
        advice.append(
            "Your current commitments are within budget. "
            "Continue tracking quotations and payments."
        )

    if actual > ZERO:
        advice.append(
            f"Your recorded actual spending is ₹{actual:,.2f}."
        )

    if planned > ZERO:
        advice.append(
            f"You have ₹{planned:,.2f} in planned expenses that are not yet confirmed."
        )

    if confirmed > ZERO:
        advice.append(
            f"You have ₹{confirmed:,.2f} in confirmed bookings."
        )

    return {
        "total_budget": total,
        "planned_expenses": committed,
        "committed_expenses": committed,
        "planned_only": planned,
        "confirmed_expenses": confirmed,
        "actual_expenses": actual,
        "remaining_budget": remaining,
        "over_budget": committed > total,
        "usage_percentage": usage_percentage,
        "expense_count": len(expenses),
        "suggested_allocations": allocations,
        "budget_advice": advice,
    }
