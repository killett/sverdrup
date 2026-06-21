import numpy as np

from sverdrup.core.evaluation import ContextKey, EvalContext
from sverdrup.eval.groundtrack import GroundTrack


def test_track_stripe_detected():
    smooth = np.tile(np.linspace(0, 1, 32), (32, 1))
    stripe = smooth + 0.3 * np.sign(np.sin(np.arange(32) * np.pi / 2))[None, :]
    ev = GroundTrack(track_wavenumber=8)
    ctx = EvalContext({ContextKey.ORBIT_GEOMETRY: {"track_spacing_nodes": 4}})
    assert (
        ev.evaluate({"field": stripe}, ctx)["track_power"]
        > ev.evaluate({"field": smooth}, ctx)["track_power"]
    )
