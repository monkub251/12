"""Shape of the profile tables — a malformed table breaks the UI at runtime."""

from __future__ import annotations

import pytest

from core.profiles import PROFILES, PULSE_STEPS, RISK_NOTICE, ULTIMATE_STEPS

KEYS = ("ULTIMATE", "PULSE")


@pytest.mark.parametrize("key", KEYS)
def test_profile_has_every_field_the_ui_reads(key):
    p = PROFILES[key]
    for field in ("name", "index", "sub", "blurb", "bullets", "steps", "impact"):
        assert p.get(field), f"{key} missing {field}"
    assert len(p["bullets"]) >= 3
    assert p["index"].isdigit()


@pytest.mark.parametrize("key", KEYS)
def test_steps_are_unique_and_callable(key):
    labels = [label for label, _ in PROFILES[key]["steps"]]
    assert len(labels) == len(set(labels)), f"{key} has a duplicate step"
    assert all(callable(fn) for _, fn in PROFILES[key]["steps"])


def test_pulse_is_a_strict_superset_of_ultimate():
    """The UI tells the user PULSE is 'everything in ULTIMATE, plus'.

    That claim has to stay true in code, not just in the copy.
    """
    head = [label for label, _ in PULSE_STEPS][: len(ULTIMATE_STEPS)]
    assert head == [label for label, _ in ULTIMATE_STEPS]
    assert len(PULSE_STEPS) > len(ULTIMATE_STEPS)


@pytest.mark.parametrize("key", KEYS)
def test_every_profile_discloses_its_risks(key):
    notice = RISK_NOTICE[key]
    assert len(notice) >= 3
    for title, why in notice:
        assert title and why
        assert len(why) > 25, f"{title}: explanation is too thin to consent to"


def test_pulse_discloses_at_least_what_ultimate_does():
    ult = {t for t, _ in RISK_NOTICE["ULTIMATE"]}
    pulse = {t for t, _ in RISK_NOTICE["PULSE"]}
    assert ult <= pulse


def test_risk_notice_covers_the_kernel_tweaks_actually_applied():
    """Memory Integrity and the CPU mitigations must never be silent."""
    for key in KEYS:
        titles = " ".join(t for t, _ in RISK_NOTICE[key]).lower()
        assert "memory integrity" in titles
        assert "spectre" in titles
