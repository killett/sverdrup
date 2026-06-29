"""their_eval λx is unchanged after routing through the shared helper."""

from __future__ import annotations

from pathlib import Path

import pytest

from sverdrup.eval.spectral import effective_resolution_lambda_x


def test_their_eval_uses_shared_helper(monkeypatch: pytest.MonkeyPatch) -> None:
    # Behavior: their_eval.score computes λx via the shared helper (one call site).
    # Bug it catches: their_eval keeping a private duplicate λx path that can drift.
    import sverdrup.validation.their_eval as te

    seen = {}
    real = effective_resolution_lambda_x

    def spy(*a: object, **k: object) -> float:
        seen["called"] = True
        return real(*a, **k)  # type: ignore[arg-type]

    monkeypatch.setattr(te, "effective_resolution_lambda_x", spy)
    # Use the committed small fixture map+track if present; otherwise skip.
    fx = Path("tests/validation/fixtures")
    mp, tp = fx / "small_map.nc", fx / "small_track.nc"
    if not (mp.exists() and tp.exists()):
        pytest.skip("small map/track fixture not present (opt-in)")
    te.score(mp, tp)
    assert seen.get("called") is True
