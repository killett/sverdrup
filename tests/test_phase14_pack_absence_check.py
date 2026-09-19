"""The absence check over the RENDERED Gate-1 pack (review pin 17, owner pin 208a).

The transfer-reading section is assembled from row fields and wrapped in
markers; this script scans exactly that section for the words that would
mean a cross-lineage interpretation slipped in while the attribution
readout is unruled. Its output is captured into the pack's close evidence.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.helpers import load_script

_check = load_script("phase14_pack_absence_check")
runner = CliRunner()


def test_the_checker_and_the_renderer_agree_on_the_markers() -> None:
    """Two scripts, one section boundary.

    Bug caught: the renderer's marker text drifting from the checker's,
    so the checker refuses (best case) or scans nothing and passes
    (worst case) over a section that was in fact rendered.
    """
    renderer = load_script("phase14_stage1_run")

    assert _check.BEGIN_MARKER == renderer.TRANSFER_BEGIN
    assert _check.END_MARKER == renderer.TRANSFER_END


def _pack(tmp_path: Path, section: str, outside: str = "") -> Path:
    path = tmp_path / "pack.md"
    path.write_text(
        f"# pack\n\n{outside}\n\n{_check.BEGIN_MARKER}\n{section}\n{_check.END_MARKER}\n\n"
        "## after\nnothing here is scanned\n"
    )
    return path


def test_a_clean_section_PASSES_and_says_so(tmp_path: Path) -> None:
    """The happy path, with the verdict word pinned (it is captured as evidence).

    Bug caught: a check that exits 0 without printing a verdict — the
    captured output would then prove nothing to the pack's reader.
    """
    pack = _pack(tmp_path, "| λx | 232.53 km |\nbridge caveat: interpretation WAITS")

    result = runner.invoke(_check.app, [str(pack)])

    assert result.exit_code == 0, result.output
    assert "PASS" in result.output
    assert str(pack) in result.output


@pytest.mark.parametrize(
    "word", ["suggests", "consistent with", "attributable", "implies"]
)
def test_each_banned_word_inside_the_section_FAILS_naming_it(
    tmp_path: Path, word: str
) -> None:
    """One test per banned word, so dropping one from the list is caught.

    Bug caught: the list shrinking (or a regex typo) so one of the four
    words passes silently — exactly the word that then ships.
    """
    pack = _pack(tmp_path, f"the residual {word} a reference offset")

    result = runner.invoke(_check.app, [str(pack)])

    assert result.exit_code == 1
    assert "FAIL" in result.output
    assert word in result.output


def test_the_check_is_case_insensitive(tmp_path: Path) -> None:
    """Sentence-initial capitals are the common case, not the exception.

    Bug caught: a case-sensitive scan passing "Suggests" at the start of a
    sentence.
    """
    pack = _pack(tmp_path, "Suggests a mechanism.")

    result = runner.invoke(_check.app, [str(pack)])

    assert result.exit_code == 1


def test_a_banned_word_OUTSIDE_the_section_does_not_fail(tmp_path: Path) -> None:
    """The scope is the assembled section, not the whole pack.

    Bug caught: an over-broad scan failing on ruled prose elsewhere —
    pin 196(c) is quoted in the pack in the owner's own words,
    "consistent with a reference offset ... consistent, not
    established", and that quotation is outside the assembled section
    by design.
    """
    pack = _pack(
        tmp_path,
        "| λx | 141.95 km |",
        outside="196(c): consistent with a reference offset — consistent, not established",
    )

    result = runner.invoke(_check.app, [str(pack)])

    assert result.exit_code == 0, result.output


def test_missing_markers_REFUSE_rather_than_pass_over_nothing(tmp_path: Path) -> None:
    """No section means nothing was checked, which must not read as PASS.

    Bug caught: the renderer's markers renamed or the splice failing, and
    the check scanning an empty string and printing PASS.
    """
    path = tmp_path / "pack.md"
    path.write_text("# pack\n\nno markers here, suggests nothing\n")

    result = runner.invoke(_check.app, [str(path)])

    assert result.exit_code == 2
    assert "marker" in result.output.lower()
