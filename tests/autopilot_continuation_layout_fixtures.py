"""Freeze the exact prior layout by copying its named columns and rows."""
from tests.autopilot_fixtures import make_prior_layout


def retain_pre_continuation_layout(home):
    make_prior_layout(home, "pre_continuation")
