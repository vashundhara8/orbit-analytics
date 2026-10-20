"""Tests for synthetic data generation logic.

Uses a tiny user set (50 users) to keep tests fast while exercising
all generation paths.
"""

import numpy as np
import pandas as pd
import pytest

# Override module-level NUM_USERS for fast tests
import python.src.generate_data as gen_mod
from python.src.generate_data import (
    CHANNELS,
    COMPANY_SIZES,
    FUNNEL_STEPS,
    INDUSTRIES,
    MRR_BY_PLAN,
    PLAN_TYPES,
    _generate_subscriptions,
    _generate_users,
    _simulate_funnel,
)

ORIGINAL_NUM_USERS = gen_mod.NUM_USERS


@pytest.fixture(autouse=True)
def _small_dataset():
    """Temporarily reduce dataset size for all tests in this module."""
    gen_mod.NUM_USERS = 50
    gen_mod.rng = np.random.default_rng(99)
    yield
    gen_mod.NUM_USERS = ORIGINAL_NUM_USERS
    gen_mod.rng = np.random.default_rng(gen_mod.SEED)


@pytest.fixture
def users() -> pd.DataFrame:
    return _generate_users()


@pytest.fixture
def funnel_result(users):
    return _simulate_funnel(users)


class TestGenerateUsers:
    def test_row_count(self, users):
        assert len(users) == 50

    def test_expected_columns(self, users):
        expected = {"user_id", "signup_date", "company_size", "industry", "acquisition_channel", "plan_type"}
        assert set(users.columns) == expected

    def test_user_ids_unique(self, users):
        assert users["user_id"].is_unique

    def test_company_sizes_valid(self, users):
        assert set(users["company_size"].unique()).issubset(set(COMPANY_SIZES))

    def test_industries_valid(self, users):
        assert set(users["industry"].unique()).issubset(set(INDUSTRIES))

    def test_channels_valid(self, users):
        assert set(users["acquisition_channel"].unique()).issubset(set(CHANNELS))

    def test_plan_types_valid(self, users):
        assert set(users["plan_type"].unique()).issubset(set(PLAN_TYPES))

    def test_signup_dates_in_range(self, users):
        assert users["signup_date"].min() >= pd.Timestamp("2024-01-01")
        assert users["signup_date"].max() <= pd.Timestamp("2025-06-30")


class TestSimulateFunnel:
    def test_events_not_empty(self, funnel_result):
        events, _ = funnel_result
        assert len(events) > 0

    def test_event_columns(self, funnel_result):
        events, _ = funnel_result
        expected = {"event_id", "user_id", "event_name", "event_ts", "device", "session_id"}
        assert set(events.columns) == expected

    def test_all_users_have_signup_event(self, funnel_result):
        _events, reached = funnel_result
        assert len(reached["signup"]) == 50

    def test_funnel_is_monotonically_decreasing(self, funnel_result):
        _, reached = funnel_result
        counts = [len(reached[step]) for step in FUNNEL_STEPS]
        for i in range(1, len(counts)):
            assert counts[i] <= counts[i - 1]

    def test_event_ids_unique(self, funnel_result):
        events, _ = funnel_result
        assert events["event_id"].is_unique


class TestGenerateSubscriptions:
    def test_one_row_per_user(self, users, funnel_result):
        _, reached = funnel_result
        subs = _generate_subscriptions(users, reached)
        assert len(subs) == len(users)

    def test_free_users_have_no_paid_date(self, users, funnel_result):
        _, reached = funnel_result
        subs = _generate_subscriptions(users, reached)
        free_subs = subs.merge(users[["user_id", "plan_type"]], on="user_id")
        free_only = free_subs[free_subs["plan_type"] == "free"]
        assert free_only["paid_start_date"].isna().all()

    def test_paid_users_only_from_project_reached(self, users, funnel_result):
        _, reached = funnel_result
        subs = _generate_subscriptions(users, reached)
        paid = subs[subs["paid_start_date"].notna()]
        project_users = reached["first_project"]
        for uid in paid["user_id"]:
            assert uid in project_users

    def test_mrr_values_valid(self, users, funnel_result):
        _, reached = funnel_result
        subs = _generate_subscriptions(users, reached)
        valid_mrr = set(MRR_BY_PLAN.values())
        assert set(subs["mrr"].unique()).issubset(valid_mrr)
