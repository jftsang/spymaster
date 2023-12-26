from random import randint
from typing import Collection, Optional


def aim_high(options: Collection[int], target: int) -> Optional[int]:
    """Try to play the smallest card that is higher than the target.
    If no such card exists, then return None.
    """
    options = [x for x in options if x > target]
    return max(options) if options else None


def aim_low(options: Collection[int], target: int) -> Optional[int]:
    """Try to play the smallest card that is lower than the target.
    If no such card exists, then return None.
    """
    options = [x for x in options if x < target]
    return min(options) if options else None


def aim(options: Collection[int], target: int, cutoff=6) -> int:
    """Try to play the card that is as close as possible to the
    target.

    If an exact match is not possible, then for a high-value target,
    try to play the smallest card that is higher than the target,
    """
    if target > 15:
        # Respond to a high prize with either the general or the
        # assassin
        target = randint(0, 1) * 15

    if target in options:
        return target

    if target > cutoff:
        if x := aim_high(options, target):
            return x
        return aim_low(options, target)
    else:
        if x := aim_low(options, target):
            return x
        return aim_high(options, target)
