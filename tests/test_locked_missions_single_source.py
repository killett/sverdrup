"""One locked-altimeter decision, one constant (hygiene: the c2 literals)."""

from __future__ import annotations

from sverdrup.adapters.altimetry import cmems_my, contract, jpl_ssha
from sverdrup.application import epoch_table
from tests.helpers import load_script


def test_every_locked_altimeter_set_is_the_contract_one() -> None:
    """Every reader of the locked altimeter tier uses the contract's set.

    CryoSat-2 is the locked evaluation instrument for every altimetry
    source, and the sites below had re-pasted ``{"c2", "c2n"}``. Identity,
    not equality: a re-pasted literal is a distinct frozenset, so a copy
    fails here even while its value still agrees. Bug caught: a site
    re-defining the set, so that a code added to the locked tier would be
    refused by one adapter yet served, fitted or sealed by another.
    """
    assert contract.LOCKED_MISSIONS == frozenset({"c2", "c2n"})
    seal_run = load_script("phase14_seal_run")
    for module, name in (
        (cmems_my, "LOCKED_MISSIONS"),
        (jpl_ssha, "LOCKED_MISSIONS"),
        (epoch_table, "LOCKED_ALTIMETERS"),
        (seal_run, "LOCKED_MISSIONS"),
    ):
        assert getattr(module, name) is contract.LOCKED_MISSIONS, module.__name__
