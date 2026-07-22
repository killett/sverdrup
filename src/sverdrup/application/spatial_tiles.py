"""Tile frames for the phase-14 spatial substrate (0d-1).

ONE shared helper emits the three nested frames every tile consumer uses:

- ``core``: the tile's own scoring/ownership region (never double-scored);
- ``solve_bbox``: core extended by the blend overlap toward existing
  neighbors (the paper's linear-blend region lives in the overlap);
- obs framing: delegated to the EXISTING ``halo_obs`` (the production
  obs-framing lesson — region = GRID NODES ± halo, never the nominal box;
  the 0.2° grid's 43.2°N overshoot sliver is load-bearing).

The anchor's degenerate frame (``anchor_frame``) reproduces the signed
10°×10° box exactly: same ``np.arange`` node construction as
``validation.params.baseline_config``, zero overlap, the operative halo.

Defaults ``tile_deg=15.0, overlap_deg=2.0`` are the paper values
(fork-d pin 1), probe-ratified at plan review; ``halo_deg`` defaults from
:func:`operative_halo_deg` — the single point of change for the
constraint-3 (kernel-scale-driven halo) decision (fork-d pin 4).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from sverdrup.adapters.altimetry.contract import BBox
from sverdrup.core.grid import GridSpec
from sverdrup.core.observations import ObsWindow
from sverdrup.validation.run import halo_obs

# Paper defaults (U2022 lineage), probe-ratified at the fork-d ruling.
TILE_DEG = 15.0
OVERLAP_DEG = 2.0

_SIDES = ("W", "E", "S", "N")


def operative_halo_deg() -> float:
    """The operative obs-halo width [degrees].

    Returns the current production practice (1.0°, the D7 default carried
    since the box era). When the constraint-3 decision ties the halo to the
    operative kernel scale, THIS function changes — nothing else.
    """
    return 1.0


@dataclass(frozen=True)
class TileFrame:
    """One tile's nested frames: core, blend overlap, obs halo.

    ``missing_neighbors`` names the sides ("W"/"E"/"S"/"N") with NO
    neighboring tile (domain edge): the solve bbox does not extend there
    and the Task-13 blend renormalizes by the actual local weight sum.
    """

    core: BBox
    overlap_deg: float
    halo_deg: float
    missing_neighbors: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        """Validate side names and non-negative widths."""
        bad = set(self.missing_neighbors) - set(_SIDES)
        if bad:
            raise ValueError(f"unknown side flag(s) {sorted(bad)}; use {_SIDES}")
        if self.overlap_deg < 0 or self.halo_deg < 0:
            raise ValueError("overlap_deg and halo_deg must be non-negative")

    @property
    def solve_bbox(self) -> BBox:
        """Core extended by the overlap toward each EXISTING neighbor."""
        m = self.missing_neighbors
        o = self.overlap_deg
        return BBox(
            lon_min=self.core.lon_min - (0.0 if "W" in m else o),
            lon_max=self.core.lon_max + (0.0 if "E" in m else o),
            lat_min=self.core.lat_min - (0.0 if "S" in m else o),
            lat_max=self.core.lat_max + (0.0 if "N" in m else o),
        )

    def obs_bbox(self, resolution_deg: float) -> BBox:
        """The obs-framing box: solve GRID NODE extent ± halo.

        Derived from the actual node extent (NOT the nominal solve box) —
        the ``halo_obs`` lesson: ``np.arange`` node construction overshoots
        nominal bounds (the recorded 43.2°N quirk), and a nominal-box cut
        silently drops the sliver and breaks bit-reproducibility.

        Args:
            resolution_deg: The solve grid resolution.

        Returns:
            The inclusive obs selection box.
        """
        grid = frame_grid(self, resolution_deg)
        return BBox(
            lon_min=float(grid.x.min()) - self.halo_deg,
            lon_max=float(grid.x.max()) + self.halo_deg,
            lat_min=float(grid.y.min()) - self.halo_deg,
            lat_max=float(grid.y.max()) + self.halo_deg,
        )


def frame_grid(frame: TileFrame, resolution_deg: float) -> GridSpec:
    """The tile's solve grid — the SAME node construction as the signed box.

    ``np.arange(min, max + res, res)`` verbatim from
    ``validation.params.baseline_config`` so the anchor frame reproduces the
    signed grid byte-identically (including its fp-overshoot behavior).

    Args:
        frame: The tile frame.
        resolution_deg: Node spacing [degrees].

    Returns:
        The lon/lat ``GridSpec`` over ``frame.solve_bbox``.
    """
    s = frame.solve_bbox
    return GridSpec.lonlat(
        lons=np.arange(s.lon_min, s.lon_max + resolution_deg, resolution_deg),
        lats=np.arange(s.lat_min, s.lat_max + resolution_deg, resolution_deg),
    )


def frame_obs(obs: ObsWindow, frame: TileFrame, resolution_deg: float) -> ObsWindow:
    """Obs selection for a tile — delegates to the EXISTING ``halo_obs``.

    No second implementation of obs framing exists: this is ``halo_obs`` on
    the tile's solve grid with the tile's halo (order preserved).

    Args:
        obs: Observations to frame.
        frame: The tile frame.
        resolution_deg: The solve grid resolution.

    Returns:
        The obs restricted to the tile's obs frame.
    """
    return halo_obs(obs, frame_grid(frame, resolution_deg), frame.halo_deg)


def anchor_frame() -> TileFrame:
    """The signed 10°×10° box as a degenerate tile (the identity anchor).

    core = the signed box, zero overlap, all four sides domain edges, the
    operative halo — so ``frame_grid`` and ``frame_obs`` reproduce the
    legacy production path byte-identically (gate-5 substrate).
    """
    return TileFrame(
        core=BBox(lon_min=295.0, lon_max=305.0, lat_min=33.0, lat_max=43.0),
        overlap_deg=0.0,
        halo_deg=operative_halo_deg(),
        missing_neighbors=frozenset(_SIDES),
    )


def tile_plan(
    domain_bbox: BBox,
    tile_deg: float = TILE_DEG,
    overlap_deg: float = OVERLAP_DEG,
    halo_deg: float | None = None,
) -> tuple[TileFrame, ...]:
    """Deterministic tile decomposition of a domain.

    Tiles are laid row-major (south→north rows, west→east within a row)
    from the domain's SW corner; ragged remainders are clipped to the
    domain and flagged via ``missing_neighbors`` on domain-edge sides.

    Args:
        domain_bbox: The full domain.
        tile_deg: Core tile size [degrees] (paper default 15.0).
        overlap_deg: Blend overlap [degrees] (paper default 2.0).
        halo_deg: Obs halo; defaults to :func:`operative_halo_deg`.

    Returns:
        The deterministic tile list.
    """
    halo = operative_halo_deg() if halo_deg is None else halo_deg
    width = domain_bbox.lon_max - domain_bbox.lon_min
    height = domain_bbox.lat_max - domain_bbox.lat_min
    if width <= 0 or height <= 0 or width > 360.0:
        raise ValueError(
            f"invalid domain {domain_bbox}: bounds must ascend and the lon "
            "span must not exceed 360 (wraparound domains are not supported "
            "by this planner)"
        )
    # The 1e-9 slack keeps an fp-marginal width (e.g. 30+1e-12 at 15-deg
    # tiles) from ceiling into a zero-width extra tile column/row.
    n_lon = max(1, int(np.ceil(width / tile_deg - 1e-9)))
    n_lat = max(1, int(np.ceil(height / tile_deg - 1e-9)))
    tiles: list[TileFrame] = []
    for iy in range(n_lat):
        lat_lo = domain_bbox.lat_min + iy * tile_deg
        lat_hi = min(lat_lo + tile_deg, domain_bbox.lat_max)
        for ix in range(n_lon):
            lon_lo = domain_bbox.lon_min + ix * tile_deg
            lon_hi = min(lon_lo + tile_deg, domain_bbox.lon_max)
            missing = set()
            if ix == 0:
                missing.add("W")
            if ix == n_lon - 1:
                missing.add("E")
            if iy == 0:
                missing.add("S")
            if iy == n_lat - 1:
                missing.add("N")
            tiles.append(
                TileFrame(
                    core=BBox(lon_lo, lon_hi, lat_lo, lat_hi),
                    overlap_deg=overlap_deg,
                    halo_deg=halo,
                    missing_neighbors=frozenset(missing),
                )
            )
    return tuple(tiles)
