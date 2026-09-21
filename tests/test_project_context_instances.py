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


def _discipline(prefix: str) -> str:
    for line in DOC.read_text().splitlines():
        if line.startswith(prefix):
            return line
    raise AssertionError(f"§7 discipline not found: {prefix!r}")


def _tagged(line: str, letter: str) -> list[int]:
    """Instance tags, matched in their BOLD form only.

    A bare ``(p2)`` inside the prose is a BACK-REFERENCE to an instance,
    not a new one — discipline 16 carries exactly that, citing (p2) again
    when describing what the review missed. Matching bare parentheses
    counts the citation as a duplicate tag and fails a correct list.
    """
    return [int(t[1:]) for t in re.findall(rf"\*\*\(({letter}\d+)\)\*\*", line)]


def test_frame_instance_tags_are_contiguous_and_unique() -> None:
    """Discipline 17's (fN) tags run f1..fN with no gaps or repeats.

    Bug caught: the same drift pin 146(b) corrected on discipline 11,
    arriving on the new list — an instance appended with a duplicate or
    skipped tag, so any count derived from the enumeration comes apart from
    it. Owner pin 242 withdrew "record the count as three" for exactly this
    reason: the tags ARE the count.
    """
    numbers = _tagged(_discipline("17. **Under pin 212(b)"), "f")

    assert numbers, "discipline 17 carries no instance tags"
    assert len(set(numbers)) == len(numbers), f"duplicate tags: {numbers}"
    assert numbers == sorted(numbers), f"tags out of order: {numbers}"
    assert numbers == list(range(1, len(numbers) + 1)), f"gap in tags: {numbers}"


def test_extreme_pricing_instance_tags_are_contiguous_and_unique() -> None:
    """Discipline 16's (pN) tags obey the same rule.

    Bug caught: discipline 16 was added with (p1)/(p2) tags and no test, so
    it could drift the way discipline 11 did before pin 146(b) mechanised
    it. Every tagged list in §7 is checked, not just the first one.
    """
    numbers = _tagged(_discipline("16. **A consequence is priced"), "p")

    assert numbers, "discipline 16 carries no instance tags"
    assert len(set(numbers)) == len(numbers), f"duplicate tags: {numbers}"
    assert numbers == list(range(1, len(numbers) + 1)), f"gap in tags: {numbers}"


def test_no_prose_count_is_restated_beside_any_tagged_list() -> None:
    """No spelled-out total sits beside the new enumerations either.

    Bug caught: pin 238 asked for "the count as three" in §7; writing that
    beside a three-item enumeration recreates the exact defect pin 146(b)
    corrected, which is why 242 withdrew it. This extends the guard from
    discipline 11 to every tagged list.
    """
    forbidden = re.compile(
        r"\b(one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s+instances?\s+to\s+date\b",
        re.IGNORECASE,
    )
    for prefix in ("16. **A consequence is priced", "17. **Under pin 212(b)"):
        assert not forbidden.search(_discipline(prefix)), prefix


def test_the_frame_discipline_records_that_the_surfaces_were_confirmed() -> None:
    """Discipline 17 keeps the evidence FOR itself, in the owner's terms.

    Bug caught: recording the frame defect while dropping the fact that all
    five authored surfaces were CONFIRMED. Without it the entry reads as
    "the surfaces were bad", which is the opposite of the lesson — a good
    surface list is still a blind spot, and it is the requester's.
    """
    text = _discipline("17. **Under pin 212(b)")
    assert "All five were confirmed." in text
    assert "the requester is the one who chose the frame" in text
    assert "OWNER's** blind spot" in text


def test_unit_of_account_instance_tags_are_contiguous_and_unique() -> None:
    """Discipline 18's (uN) tags run u1..uN with no gaps or repeats.

    Bug caught: the drift pin 146(b) corrected, arriving on the newest
    list. Owner pin 248 asked for the instances tagged and the count
    derived, so the tags are the count here too.
    """
    numbers = _tagged(_discipline("18. **A price is stated in a UNIT"), "u")

    assert numbers, "discipline 18 carries no instance tags"
    assert len(set(numbers)) == len(numbers), f"duplicate tags: {numbers}"
    assert numbers == list(range(1, len(numbers) + 1)), f"gap in tags: {numbers}"


def test_the_unit_discipline_keeps_the_owner_authored_instance() -> None:
    """(u3) is present and is marked as the owner's own.

    Bug caught: recording only the executor's two instances. Pin 248 is
    explicit that the owner's ratification is one of the three and is
    tagged as the owner's — a list that quietly drops it would teach the
    wrong lesson about where this failure comes from.
    """
    text = _discipline("18. **A price is stated in a UNIT")
    assert "owner-authored, pin 244" in text
    assert "only point at which the two" in text
    assert "not 'check the arithmetic'" in text


def test_the_withdrawn_ordering_claim_is_not_asserted_in_section_7() -> None:
    """Discipline 17 no longer repeats the false "every exponent" claim.

    Bug caught (owner pin 244b): the withdrawn claim surviving in §7 after
    being struck from the document and the node. §7 is the standing list a
    future reader consults, so a claim left live here outlives its
    withdrawal everywhere else.
    """
    text = _discipline("17. **Under pin 212(b)")
    assert "dearer at every exponent above zero" not in text
    assert "ITSELF WITHDRAWN AND FALSE" in text
    assert "f CONVEX" in text


def test_deliverable_review_instance_tags_are_contiguous_and_unique() -> None:
    """Discipline 19's (dN) tags run d1..dN with no gaps or repeats.

    Bug caught: the drift pin 146(b) corrected, on the newest list. Every
    tagged list in §7 is now checked.
    """
    numbers = _tagged(_discipline("19. **When a deliverable is overturned"), "d")

    assert numbers, "discipline 19 carries no instance tags"
    assert len(set(numbers)) == len(numbers), f"duplicate tags: {numbers}"
    assert numbers == list(range(1, len(numbers) + 1)), f"gap in tags: {numbers}"


def test_the_deliverable_discipline_is_marked_as_the_owners_own() -> None:
    """(d1) records that the instance and the rule are both the owner's.

    Bug caught: recording the three overturns as the executor's failures
    and dropping that the decision to order each rebuild was the owner's.
    Pin 253 is explicit that the pattern being catalogued is the ruling
    one, not the building one — a list that quietly reassigns it teaches
    the wrong lesson about where this failure comes from.
    """
    text = _discipline("19. **When a deliverable is overturned")
    assert "owner-authored, and the instance is the owner's own" in text
    assert "VALIDITY IS PRIOR TO PRICE" in text
    assert "was available at the first overturn and" in text
