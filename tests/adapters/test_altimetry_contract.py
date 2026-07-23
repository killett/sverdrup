"""Along-track source contract + conformance suite (phase-14 Task 1).

``AltimetryConformance`` is the suite every adapter must pass: subclass it
and override the ``source_factory`` / ``query`` fixtures only (Task-2/3/6
adapters do exactly that). The synthetic adapter runs it in public CI with
no external data.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pytest

from sverdrup.adapters.altimetry import (
    AlongTrackSource,
    BBox,
    SourceDescriptor,
    apply_superobs,
)
from sverdrup.adapters.altimetry.synthetic import SyntheticSource
from sverdrup.core.observations import ObsWindow

# ---------------------------------------------------------------------------
# SourceDescriptor unit tests
# ---------------------------------------------------------------------------

_MANIFEST = (
    ("b/file2.nc", "b" * 64),
    ("a/file1.nc", "a" * 64),
)


def test_descriptor_normalizes_manifest_order() -> None:
    """Two input orderings yield equal descriptors and equal shas."""
    d1 = SourceDescriptor("s", "v1", _MANIFEST)
    d2 = SourceDescriptor("s", "v1", tuple(reversed(_MANIFEST)))
    assert d1.content_manifest == tuple(sorted(_MANIFEST))
    assert d1 == d2
    assert d1.manifest_sha() == d2.manifest_sha()


@pytest.mark.parametrize(
    "other",
    [
        SourceDescriptor("s2", "v1", _MANIFEST),
        SourceDescriptor("s", "v2", _MANIFEST),
        SourceDescriptor(
            "s", "v1", (("a/file1.nc", "a" * 64), ("b/file2.nc", "c" * 64))
        ),
        SourceDescriptor("s", "v1", (("a/file1.nc", "a" * 64),)),
    ],
)
def test_manifest_sha_sensitive_to_every_field(other: SourceDescriptor) -> None:
    """Changing source id, version, one file sha, or the file set moves the sha."""
    base = SourceDescriptor("s", "v1", _MANIFEST)
    assert base.manifest_sha() != other.manifest_sha()


def test_manifest_sha_is_hex_digest() -> None:
    """The sha is a 64-char lowercase hex string (sha256)."""
    sha = SourceDescriptor("s", "v1", _MANIFEST).manifest_sha()
    assert len(sha) == 64
    assert set(sha) <= set("0123456789abcdef")


# ---------------------------------------------------------------------------
# apply_superobs hook (fork-a pin 4)
# ---------------------------------------------------------------------------


def _tiny_window() -> ObsWindow:
    from sverdrup.core.observations import DiagonalErrorModel

    return ObsWindow.from_arrays(
        np.array([300.0]),
        np.array([40.0]),
        np.array([1.0]),
        np.array([0.1]),
        DiagonalErrorModel(np.array([1e-3])),
        mission=np.array(["synA"]),
    )


def test_apply_superobs_is_identity_without_cfg() -> None:
    """cfg=None returns the SAME object — no transform, no copy, no mutation."""
    obs = _tiny_window()
    assert apply_superobs(obs) is obs


def test_apply_superobs_refuses_unknown_cfg() -> None:
    """An unknown transform kind must refuse, not silently ignore."""
    with pytest.raises(NotImplementedError, match="super-obs"):
        apply_superobs(_tiny_window(), cfg={"radius_km": 25.0})


def test_apply_superobs_challenge_coarsen_hand_values() -> None:
    """challenge-coarsen: mean-of-n blocks per (mission, day), trim rest.

    7 samples, n=5 -> ONE super-ob = mean of the first 5; samples 6-7
    trimmed. Values/coords hand-computed; a no-trim or off-by-one block
    boundary moves them.
    """
    from sverdrup.core.observations import DiagonalErrorModel

    n = 7
    obs = ObsWindow.from_arrays(
        np.arange(n, dtype=float),
        np.arange(n, dtype=float) * 2.0,
        np.full(n, 3.25),
        np.arange(n, dtype=float) * 10.0,
        DiagonalErrorModel(np.full(n, 1e-3)),
        mission=np.full(n, "synA"),
    )
    out = apply_superobs(obs, cfg={"kind": "challenge-coarsen", "n": 5})
    assert len(out) == 1
    c = out.coords()
    assert c[0, 0] == pytest.approx(2.0)  # mean(0..4)
    assert c[0, 1] == pytest.approx(4.0)
    assert out.values()[0] == pytest.approx(20.0)
    m = out.mission
    assert m is not None and m[0] == "synA"


def test_apply_superobs_coarsen_blocks_never_cross_missions() -> None:
    """Blocks reset at mission changes — a cross-mission mean is corrupt."""
    from sverdrup.core.observations import DiagonalErrorModel

    obs = ObsWindow.from_arrays(
        np.array([0.0, 2.0, 10.0, 12.0]),
        np.zeros(4),
        np.full(4, 1.5),
        np.array([1.0, 3.0, 100.0, 102.0]),
        DiagonalErrorModel(np.full(4, 1e-3)),
        mission=np.array(["synA", "synA", "synB", "synB"]),
    )
    out = apply_superobs(obs, cfg={"kind": "challenge-coarsen", "n": 2})
    assert len(out) == 2
    assert out.values()[0] == pytest.approx(2.0)  # synA pair only
    assert out.values()[1] == pytest.approx(101.0)  # synB pair only


# ---------------------------------------------------------------------------
# The conformance suite (adapters subclass with fixture overrides only)
# ---------------------------------------------------------------------------


class AltimetryConformance:
    """Contract conformance: subclass and override the two fixtures."""

    @pytest.fixture
    def source_factory(self) -> Callable[[], AlongTrackSource]:
        """Return a zero-arg factory building a FRESH source instance."""
        raise NotImplementedError("adapter test class must override")

    @pytest.fixture
    def query(self) -> tuple[BBox, np.datetime64, np.datetime64]:
        """A (bbox, t0, t1) query with data present for the adapter."""
        raise NotImplementedError("adapter test class must override")

    # -- helpers ----------------------------------------------------------

    @staticmethod
    def _arrays(obs: ObsWindow) -> tuple[np.ndarray, ...]:
        c = obs.coords()
        mission = obs.mission
        assert mission is not None, "contract: obs must be mission-tagged"
        return c[:, 0], c[:, 1], c[:, 2], obs.values(), mission

    # -- tests ------------------------------------------------------------

    def test_region_clipping_exact(
        self,
        source_factory: Callable[[], AlongTrackSource],
        query: tuple[BBox, np.datetime64, np.datetime64],
    ) -> None:
        """A sub-box load equals the mask-restriction of the full load."""
        bbox, t0, t1 = query
        src = source_factory()
        full = src.load(bbox, t0, t1)
        sub_bbox = BBox(
            lon_min=bbox.lon_min + (bbox.lon_max - bbox.lon_min) * 0.25,
            lon_max=bbox.lon_min + (bbox.lon_max - bbox.lon_min) * 0.75,
            lat_min=bbox.lat_min + (bbox.lat_max - bbox.lat_min) * 0.25,
            lat_max=bbox.lat_min + (bbox.lat_max - bbox.lat_min) * 0.75,
        )
        sub = src.load(sub_bbox, t0, t1)
        lon, lat, t, v, m = self._arrays(full)
        keep = sub_bbox.contains(lon, lat)
        assert keep.any(), "fixture query must leave obs in the sub-box"
        s_lon, s_lat, s_t, s_v, s_m = self._arrays(sub)
        assert np.array_equal(s_lon, lon[keep])
        assert np.array_equal(s_lat, lat[keep])
        assert np.array_equal(s_t, t[keep])
        assert np.array_equal(s_v, v[keep])
        assert np.array_equal(s_m, m[keep])

    def test_time_clipping_exact(
        self,
        source_factory: Callable[[], AlongTrackSource],
        query: tuple[BBox, np.datetime64, np.datetime64],
    ) -> None:
        """A sub-interval load equals the [t0, t1) mask of the full load."""
        bbox, t0, t1 = query
        src = source_factory()
        full = src.load(bbox, t0, t1)
        mid = t0 + (t1 - t0) // 2
        sub = src.load(bbox, t0, mid)
        lon, lat, t, v, m = self._arrays(full)
        mid_days = float((mid - src.time_epoch()) / np.timedelta64(1, "D"))
        keep = t < mid_days
        assert keep.any() and not keep.all(), "fixture must straddle the cut"
        s_lon, s_lat, s_t, s_v, s_m = self._arrays(sub)
        assert np.array_equal(s_t, t[keep])
        assert np.array_equal(s_lon, lon[keep])
        assert np.array_equal(s_lat, lat[keep])
        assert np.array_equal(s_v, v[keep])
        assert np.array_equal(s_m, m[keep])

    def test_mission_filter_exact(
        self,
        source_factory: Callable[[], AlongTrackSource],
        query: tuple[BBox, np.datetime64, np.datetime64],
    ) -> None:
        """Filtering to one mission equals the mask-restriction of the full load."""
        bbox, t0, t1 = query
        src = source_factory()
        full = src.load(bbox, t0, t1)
        lon, lat, t, v, m = self._arrays(full)
        target = str(src.missions()[0])
        one = src.load(bbox, t0, t1, missions=[target])
        keep = m == target
        assert keep.any(), "fixture query must contain the first mission"
        o_lon, o_lat, o_t, o_v, o_m = self._arrays(one)
        assert set(np.unique(o_m)) == {target}
        assert np.array_equal(o_lon, lon[keep])
        assert np.array_equal(o_lat, lat[keep])
        assert np.array_equal(o_t, t[keep])
        assert np.array_equal(o_v, v[keep])

    def test_unknown_mission_refused(
        self,
        source_factory: Callable[[], AlongTrackSource],
        query: tuple[BBox, np.datetime64, np.datetime64],
    ) -> None:
        """An unknown mission code raises, never a silent empty window."""
        bbox, t0, t1 = query
        with pytest.raises(ValueError, match="mission"):
            source_factory().load(bbox, t0, t1, missions=["not-a-mission"])

    def test_descriptor_stable_across_instantiations(
        self, source_factory: Callable[[], AlongTrackSource]
    ) -> None:
        """Two fresh instances describe identical content identically."""
        d1 = source_factory().descriptor()
        d2 = source_factory().descriptor()
        assert d1 == d2
        assert d1.manifest_sha() == d2.manifest_sha()

    def test_manifest_nonempty_and_sha_content_sensitive(
        self, source_factory: Callable[[], AlongTrackSource]
    ) -> None:
        """Manifest carries per-file shas (pin 3); any byte change moves the sha."""
        desc = source_factory().descriptor()
        assert len(desc.content_manifest) >= 1
        rel, sha = desc.content_manifest[0]
        flipped = "0" if sha[0] != "0" else "1"
        mutated = SourceDescriptor(
            desc.source_id,
            desc.dataset_version,
            ((rel, flipped + sha[1:]),) + desc.content_manifest[1:],
        )
        assert mutated.manifest_sha() != desc.manifest_sha()

    def test_load_deterministic(
        self,
        source_factory: Callable[[], AlongTrackSource],
        query: tuple[BBox, np.datetime64, np.datetime64],
    ) -> None:
        """Two loads (fresh instances) are byte-equal, dtypes included."""
        bbox, t0, t1 = query
        a = source_factory().load(bbox, t0, t1)
        b = source_factory().load(bbox, t0, t1)
        for x, y in zip(self._arrays(a), self._arrays(b), strict=True):
            assert np.array_equal(x, y)
            assert x.dtype == y.dtype


# ---------------------------------------------------------------------------
# Synthetic adapter: conformance + analytic pins
# ---------------------------------------------------------------------------

_GLOBE = BBox(lon_min=0.0, lon_max=360.0, lat_min=-90.0, lat_max=90.0)


class TestSyntheticConformance(AltimetryConformance):
    """The synthetic adapter passes the full suite in CI, no external data."""

    @pytest.fixture
    def source_factory(self) -> Callable[[], AlongTrackSource]:
        return SyntheticSource

    @pytest.fixture
    def query(self) -> tuple[BBox, np.datetime64, np.datetime64]:
        return (_GLOBE, np.datetime64("2017-01-05"), np.datetime64("2017-01-09"))


def _day(d: int) -> np.datetime64:
    return np.datetime64("2017-01-01") + np.timedelta64(d, "D")


def test_synthetic_obs_density_500_per_mission_day() -> None:
    """One full-globe day carries exactly 500 obs per mission."""
    src = SyntheticSource()
    obs = src.load(_GLOBE, _day(3), _day(4))
    mission = obs.mission
    assert mission is not None
    counts = {m: int((mission == m).sum()) for m in src.missions()}
    assert counts == {"synA": 500, "synB": 500}


def test_synthetic_synA_repeats_every_10_days_synB_drifts() -> None:
    """synA ground track coords repeat at lag 10 d; synB's do not."""
    src = SyntheticSource()
    day0 = src.load(_GLOBE, _day(0), _day(1))
    day10 = src.load(_GLOBE, _day(10), _day(11))

    def track(obs: ObsWindow, m: str) -> np.ndarray:
        mission = obs.mission
        assert mission is not None
        return obs.coords()[mission == m][:, :2]

    assert np.array_equal(track(day0, "synA"), track(day10, "synA"))
    assert not np.array_equal(track(day0, "synB"), track(day10, "synB"))


def test_synthetic_time_boundary_half_open() -> None:
    """Obs at exactly t1 are excluded; at exactly t0 included."""
    src = SyntheticSource()
    obs = src.load(_GLOBE, _day(2), _day(3))
    t = obs.coords()[:, 2]
    assert t.min() == 2.0  # the day-start obs at t0 is included
    assert t.max() < 3.0  # the day-start obs at t1 is excluded


def test_synthetic_values_are_structured_ssh() -> None:
    """Values are finite and non-constant (a real field, not zeros)."""
    obs = SyntheticSource().load(_GLOBE, _day(0), _day(2))
    v = obs.values()
    assert np.isfinite(v).all()
    assert np.std(v) > 0.0
    assert v.dtype == np.float64
