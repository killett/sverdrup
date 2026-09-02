"""Owner pin 146(b) — §7 discipline 11's count is derived, not restated.

The entry said "Six instances to date" and enumerated seven. A stated
count that drifts from its own enumeration is a small instance of the
family the list exists to catalogue, so the count is now derived from
`(iN)` tags and this test is what makes "derived" mechanical rather than
a promise.
"""

from __future__ import annotations

import re
from pathlib import Path

DOC = Path("docs/project-context.md")


def _discipline_11() -> str:
    for line in DOC.read_text().splitlines():
        if line.startswith("11. Every quantitative gate"):
            return line
    raise AssertionError("§7 discipline 11 not found")


def test_instance_tags_are_contiguous_and_unique() -> None:
    """The tags run i1..iN with no gaps and no repeats.

    Bug caught: an instance appended with a duplicate or skipped tag,
    which is how the enumeration and any count derived from it come
    apart — the exact drift pin 146(b) is correcting.
    """
    tags = re.findall(r"\((i\d+)\)", _discipline_11())
    numbers = [int(t[1:]) for t in tags]

    assert numbers, "the instance list carries no tags"
    assert len(set(numbers)) == len(numbers), f"duplicate instance tags: {numbers}"
    assert numbers == sorted(numbers), f"instance tags out of order: {numbers}"
    assert numbers == list(range(1, len(numbers) + 1)), (
        f"gap in instance tags: {numbers}"
    )


def test_no_prose_count_is_restated_beside_the_list() -> None:
    """No spelled-out total sits next to the enumeration.

    Bug caught: the original defect returning — someone writes "Nine
    instances to date" beside the tags, and the two drift apart again the
    next time an instance is added. The tags are the count.
    """
    text = _discipline_11()
    forbidden = re.compile(
        r"\b(one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s+instances?\s+to\s+date\b",
        re.IGNORECASE,
    )
    assert not forbidden.search(text), (
        "a restated count is present; the count must be derived from the "
        "(iN) tags, per owner pin 146(b)"
    )


def test_the_enforcement_instance_is_recorded() -> None:
    """Pin 140(b)'s instance, in the owner's words, is in the list.

    Bug caught: the correction being described in a commit message or a
    progress note instead of the standing list — which is where the next
    reader looks, and the reason the owner asked for it there.
    """
    text = _discipline_11()
    assert "A SCHEMA FIELD THAT ONLY INSPECTS VOLUNTEERS INSPECTS NOTHING" in text
    assert "pin 140(b)" in text
