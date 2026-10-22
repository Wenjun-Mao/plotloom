"""Aggregate budgets are optional; provider and dispatch safety are independent."""


def exceeds_budget(amount: int, limit: int | None) -> bool:
    return limit is not None and amount > limit


def budget_within_authority(limit: int | None, authority: int | None) -> bool:
    """An uncapped request cannot fit inside a finite frozen grant."""
    return authority is None or (limit is not None and limit <= authority)
