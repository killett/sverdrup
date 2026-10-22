"""``select_reduction`` refuses an operator with no representation (hygiene #32)."""

from __future__ import annotations

import pytest

from sverdrup.distributions.reduction import select_reduction


class _OpWithoutRepresentation:
    """A covariance operator that forgot the protocol's ``representation``."""

    fidelity = None


class _Dist:
    cov_op = _OpWithoutRepresentation()


def test_an_operator_without_a_representation_is_refused_not_defaulted() -> None:
    """Bug caught: a new operator (a dense or FEM one, say) that never set
    ``representation`` being silently persisted as low-rank+diag — the
    reducer then materialises a factor the operator does not have, and the
    persisted product carries the wrong representation tag."""
    with pytest.raises(TypeError, match="representation"):
        select_reduction(_Dist())
