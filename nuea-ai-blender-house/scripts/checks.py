"""Collect every failing item of a check in one run instead of stopping at the first assert (references/working-economy.md, rule 5).

    exec(open(S + "checks.py").read())
    each(pieces.items(), lambda kv: _check_bends(*kv), "bends")   # one AssertionError listing every failing piece, each with its [tag]

A mutation suite still sees its tag: the combined message holds every failure's text. Set CHECK_FIRST=1 to stop at the first one.
Only AssertionError is collected: any other error (a missing object, a KeyError) stops the run as usual.
"""
import os


def each(items, fn, what="check"):
    """Run fn(item) on every item. Raise one AssertionError that lists every failure, or the first one when CHECK_FIRST=1."""
    fails = []
    for it in items:
        try:
            fn(it)
        except AssertionError as e:
            if os.environ.get("CHECK_FIRST", "") not in ("", "0"):
                raise
            fails.append(str(e))
    if fails:
        raise AssertionError(f"{len(fails)} failing in {what}:\n" + "\n".join(fails))


def _selftest():
    os.environ.pop("CHECK_FIRST", None)
    def fn(x):
        assert x % 2, f"[odd] {x} is even"
    try:
        each(range(5), fn, "numbers")
    except AssertionError as e:
        assert "3 failing" in str(e) and "[odd] 4" in str(e), str(e)
    else:
        raise AssertionError("each() passed three even numbers")
    each([1, 3], fn)   # all good: no raise
    return "checks ok"


if __name__ == "__main__":
    print(_selftest())
