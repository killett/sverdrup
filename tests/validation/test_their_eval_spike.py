"""De-risk spike: their scorer on a shipped map reproduces its leaderboard row.

The de-risk premise is "their eval is ground truth": running their own scoring
code on one of their own shipped reconstruction maps must reproduce that map's
published (mu, sigma, lambda_x) leaderboard row. We anchor on whichever shipped
map is present locally:

- BASELINE (the OI baseline, 0.85/0.09/140) is the milestone's primary anchor,
  but is not on the reachable MEOM mirror (AVISO hosts it; see audit trail).
- DUACS (0.88/0.07/152) IS on the MEOM mirror and serves as the runnable anchor.

Each case skips cleanly when its map (or the withheld track) is absent.
"""

import pytest

from sverdrup.validation.config import ValidationConfig
from sverdrup.validation.their_eval import score

pytestmark = pytest.mark.external  # requires the vendored submodule + challenge data

# (map filename, published mu, sigma, lambda_x) for shipped leaderboard rows.
_PUBLISHED = [
    pytest.param("OSE_ssh_mapping_BASELINE.nc", 0.85, 0.09, 140.0, id="baseline"),
    pytest.param("OSE_ssh_mapping_DUACS.nc", 0.88, 0.07, 152.0, id="duacs"),
]


def _find(root, pattern):
    """Return the first file under ``root`` matching a recursive glob."""
    matches = sorted(root.rglob(pattern))
    return matches[0] if matches else None


@pytest.mark.parametrize(
    ("map_name", "pub_mu", "pub_sigma", "pub_lambda_x"), _PUBLISHED
)
def test_their_eval_reproduces_published_row(map_name, pub_mu, pub_sigma, pub_lambda_x):
    """Their scorer on their own shipped map reproduces that leaderboard row.

    Catches version-skew (pinned eval != leaderboard eval, including pyinterp
    API drift) and a broken import path BEFORE any adapter is built. All three
    numbers must land, not just mu.
    """
    cfg = ValidationConfig.load()
    root = cfg.data_root
    map_path = _find(root, map_name)
    track_path = _find(root, "*c2*l3*.nc")
    if map_path is None or track_path is None:
        pytest.skip(f"{map_name} or the Cryosat-2 track not present under {root}")

    mu, sigma, lambda_x = score(map_path, track_path)

    assert mu == pytest.approx(pub_mu, abs=0.02), f"mu={mu}"
    assert sigma == pytest.approx(pub_sigma, abs=0.02), f"sigma={sigma}"
    assert lambda_x == pytest.approx(pub_lambda_x, abs=10.0), f"lambda_x={lambda_x}"
