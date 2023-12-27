from random import randint
from typing import Collection, Optional


def prefer(*options: Optional[int]) -> Optional[int]:
    """Given a list of options, return the first one that isn't None.
    Return None if they are all None.

    We're using 0 for the assassin and None to denote that no option is
    available. A test like "if x" can't tell between them, so we have to
    use None checks instead, which are a little more verbose. Hence this
    helper function. Note that they all get evaluated; there's no short-
    circuiting.
    """
    for o in options:
        if o is not None:
            return o
    return None


def aim_high(options: Collection[int], target: int) -> Optional[int]:
    """Try to play the smallest card that is higher than the target.
    If no such card exists, then return None.
    """
    options = [x for x in options if x > target]
    return max(options, default=None)


def aim_low(options: Collection[int], target: int) -> Optional[int]:
    """Try to play the smallest card (including the assassin) that is
    lower than the target. If no such card exists, then return None.
    """
    options = [x for x in options if x < target]
    return min(options, default=None)


def aim(options: Collection[int], target: int, cutoff=6) -> int:
    """Try to play the card that is as close as possible to the
    target.

    If an exact match is not possible, then for a high-value target, try
    to play, in this order:
        1. the smallest card higher than the target
        2. the assassin
        3. the smallest card other than the assassin

    and for a low-value target:
        1. the assassin
        2. the smallest card (other than the assassin)
        3. the smallest card higher than the target
    """
    if target > 15:
        # A high target might be treated as 0 (i.e. try to play the assassin)
        target = randint(0, 1) * 15

    if target in options:
        return target

    if target > cutoff:
        return prefer(aim_high(options, target), aim_low(options, target))
    else:
        return prefer(aim_low(options, target), aim_high(options, target))


def mx(
    mine: Collection[int], theirs: Collection[int], low: int, high: int
) -> Optional[int]:
    """Aim to win in the range [low, high]. Play our smallest option in
    this range that beats their best option in this range. Return None
    if no such option exists.
    """
    their_best = max((x for x in theirs if low <= x <= high), default=low)
    return min((x for x in mine if their_best <= x <= high), default=None)


def chuck(mine: Collection[int]) -> int:
    """Attempt to play a low card. Prioritise playing cards above 4 (to
    have a shot of winning); if no such cards are available then play
    the absolutely lowest cards. Only play the assassin if nothing else
    is available.
    """
    lower = randint(1, 4)
    return prefer(
        min((x for x in mine if x >= lower), default=None),
        min((x for x in mine if x > 0), default=None),
        0,
    )
