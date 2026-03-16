import numpy as np
import pandas as pd
import pytest


def _make_segments_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "cate": [0.012, 0.007, 0.002, -0.004],
            "baseline_prob": [0.001, 0.002, 0.003, 0.020],
            "segment": ["Persuadables", "Sure Things", "Lost Causes", "Sleeping Dogs"],
            "debug_col": ["a", "b", "c", "d"],
        }
    )


def _make_roi_results() -> dict:
    return {
        "full_targeting": {
            "n_targeted": 8,
            "n_incremental_conv": 0.8,
            "total_cost": 8.0,
            "roi": 0.1,
        },
        "random_targeting": [
            {"budget_pct": 0.1, "n_targeted": 1, "n_incremental_conv": 0.1, "roi": 0.1},
            {"budget_pct": 0.2, "n_targeted": 2, "n_incremental_conv": 0.2, "roi": 0.1},
            {"budget_pct": 0.3, "n_targeted": 2, "n_incremental_conv": 0.2, "roi": 0.1},
            {"budget_pct": 1.0, "n_targeted": 8, "n_incremental_conv": 0.8, "roi": 0.1},
        ],
        "precision_targeting": {
            "n_targeted": 2,
            "n_incremental_conv": 0.5,
            "total_cost": 2.0,
            "roi": 0.25,
            "budget_saving_pct": 75.0,
            "conversion_retention_pct": 62.5,
        },
        "budget_sweep": [
            {"budget_pct": 0.1, "n_targeted": 1, "cumulative_uplift": 0.2},
            {"budget_pct": 1.0, "n_targeted": 8, "cumulative_uplift": 0.8},
        ],
        "_meta": {
            "ate_observed": 0.11,
            "ate_from_cate": 0.1,
            "full_incremental_observed": 0.88,
            "full_incremental_from_cate": 0.8,
        },
    }


class TestPrepareUserSegmentsExport:
    def test_returns_canonical_export_dataframe(self):
        import src.business as business

        segments_df = _make_segments_df()

        export_df = business.prepare_user_segments_export(
            segments_df,
            customer_id=[11, 12, 13, 14],
            score_date="2026-03-08",
            model_version="phase3_2026-03-08_x_learner",
        )

        expected = pd.DataFrame(
            {
                "customer_id": [11, 12, 13, 14],
                "score_date": ["2026-03-08"] * 4,
                "model_version": ["phase3_2026-03-08_x_learner"] * 4,
                "uplift_score": [0.012, 0.007, 0.002, -0.004],
                "cate": [0.012, 0.007, 0.002, -0.004],
                "baseline_prob": [0.001, 0.002, 0.003, 0.020],
                "segment": pd.Series(["Persuadables", "Sure Things", "Lost Causes", "Sleeping Dogs"], dtype="string"),
            }
        )

        assert list(export_df.columns) == [
            "customer_id",
            "score_date",
            "model_version",
            "uplift_score",
            "cate",
            "baseline_prob",
            "segment",
        ]
        assert export_df is not segments_df
        pd.testing.assert_frame_equal(export_df.reset_index(drop=True), expected.reset_index(drop=True))

    @pytest.mark.parametrize(
        "missing_col",
        ["cate", "baseline_prob", "segment"],
    )
    def test_rejects_missing_required_columns(self, missing_col: str):
        import src.business as business

        segments_df = _make_segments_df().drop(columns=[missing_col])

        with pytest.raises(ValueError, match="missing required columns"):
            business.prepare_user_segments_export(
                segments_df,
                customer_id=[11, 12, 13, 14],
                score_date="2026-03-08",
                model_version="phase3_2026-03-08_x_learner",
            )

    def test_rejects_invalid_values_and_unknown_segments(self):
        import src.business as business

        bad_numeric_df = _make_segments_df()
        bad_numeric_df.loc[0, "cate"] = np.nan
        with pytest.raises(ValueError, match="cate/baseline_prob"):
            business.prepare_user_segments_export(
                bad_numeric_df,
                customer_id=[11, 12, 13, 14],
                score_date="2026-03-08",
                model_version="phase3_2026-03-08_x_learner",
            )

        bad_probability_df = _make_segments_df()
        bad_probability_df.loc[0, "baseline_prob"] = 1.2
        with pytest.raises(ValueError, match=r"baseline_prob outside \[0, 1\]"):
            business.prepare_user_segments_export(
                bad_probability_df,
                customer_id=[11, 12, 13, 14],
                score_date="2026-03-08",
                model_version="phase3_2026-03-08_x_learner",
            )

        bad_segment_df = _make_segments_df()
        bad_segment_df.loc[0, "segment"] = "High Value"
        with pytest.raises(ValueError, match="unknown segment"):
            business.prepare_user_segments_export(
                bad_segment_df,
                customer_id=[11, 12, 13, 14],
                score_date="2026-03-08",
                model_version="phase3_2026-03-08_x_learner",
            )

    def test_rejects_warning_tagged_segments(self):
        import src.business as business

        segments_df = _make_segments_df()
        segments_df["_warning"] = "Sure Things < 100"

        with pytest.raises(ValueError, match="refuse to export formal artifact"):
            business.prepare_user_segments_export(
                segments_df,
                customer_id=[11, 12, 13, 14],
                score_date="2026-03-08",
                model_version="phase3_2026-03-08_x_learner",
            )

    def test_rejects_invalid_export_metadata(self):
        import src.business as business

        segments_df = _make_segments_df()

        with pytest.raises(ValueError, match="score_date"):
            business.prepare_user_segments_export(
                segments_df,
                customer_id=[11, 12, 13, 14],
                score_date="not-a-date",
                model_version="phase3_2026-03-08_x_learner",
            )

        with pytest.raises(ValueError, match="model_version"):
            business.prepare_user_segments_export(
                segments_df,
                customer_id=[11, 12, 13, 14],
                score_date="2026-03-08",
                model_version="   ",
            )

    def test_rejects_invalid_customer_id_contract(self):
        import src.business as business

        segments_df = _make_segments_df()

        with pytest.raises(ValueError, match="customer_id length mismatch"):
            business.prepare_user_segments_export(
                segments_df,
                customer_id=[1, 2, 3],
                score_date="2026-03-08",
                model_version="phase3_2026-03-08_x_learner",
            )

        with pytest.raises(ValueError, match="customer_id must be unique"):
            business.prepare_user_segments_export(
                segments_df,
                customer_id=[1, 1, 2, 3],
                score_date="2026-03-08",
                model_version="phase3_2026-03-08_x_learner",
            )


class TestPrepareTableauPolicyCompareExport:
    def test_returns_expected_policy_compare_rows(self):
        import src.business as business

        export_df = business.prepare_tableau_policy_compare_export(_make_roi_results())

        expected = pd.DataFrame(
            {
                "policy_name": [
                    "Full Targeting",
                    "Random Targeting (25% budget comparator)",
                    "Persuadables only",
                ],
                "policy_role": ["reference_full", "derived_baseline", "selected_policy"],
                "budget_pct": [1.0, 0.25, 0.25],
                "n_targeted": [8, 2, 2],
                "incremental_conversion_proxy": [0.8, 0.2, 0.5],
                "roi_proxy": [0.1, 0.1, 0.25],
                "budget_saving_pct": [0.0, 75.0, 75.0],
                "conversion_retention_pct": [100.0, 25.0, 62.5],
                "roi_proxy_ratio_vs_full": [1.0, 1.0, 2.5],
                "selected_policy": [False, False, True],
                "derived_baseline": [False, True, False],
                "display_order": [1, 2, 3],
            }
        )

        pd.testing.assert_frame_equal(export_df.reset_index(drop=True), expected)

    def test_prefers_exact_random_row_when_matching_budget_exists(self):
        import src.business as business

        roi_results = _make_roi_results()
        roi_results["random_targeting"].append(
            {"budget_pct": 0.25, "n_targeted": 2, "n_incremental_conv": 0.23, "roi": 0.115}
        )

        export_df = business.prepare_tableau_policy_compare_export(roi_results)
        random_row = export_df.loc[export_df["policy_role"] == "derived_baseline"].iloc[0]

        assert random_row["incremental_conversion_proxy"] == pytest.approx(0.23)
        assert random_row["roi_proxy"] == pytest.approx(0.115)
        assert random_row["conversion_retention_pct"] == pytest.approx(28.75)

    def test_supports_missing_meta_fallback_for_random_comparator(self):
        import src.business as business

        roi_results = _make_roi_results()
        del roi_results["_meta"]

        export_df = business.prepare_tableau_policy_compare_export(roi_results)
        random_row = export_df.loc[export_df["policy_role"] == "derived_baseline"].iloc[0]

        assert random_row["incremental_conversion_proxy"] == pytest.approx(0.2)
        assert random_row["roi_proxy"] == pytest.approx(0.1)

    def test_rejects_inconsistent_precision_summary_fields(self):
        import src.business as business

        roi_results = _make_roi_results()
        roi_results["precision_targeting"]["budget_saving_pct"] = 70.0

        with pytest.raises(ValueError, match="budget_saving_pct inconsistent"):
            business.prepare_tableau_policy_compare_export(roi_results)

    def test_rejects_non_positive_full_policy_incremental_uplift(self):
        import src.business as business

        roi_results = _make_roi_results()
        roi_results["full_targeting"]["n_incremental_conv"] = 0.0
        roi_results["full_targeting"]["roi"] = 0.0
        roi_results["precision_targeting"]["conversion_retention_pct"] = 999.0

        with pytest.raises(ValueError, match="full_targeting.n_incremental_conv must be > 0"):
            business.prepare_tableau_policy_compare_export(roi_results)


class TestSimulateRoi:
    def test_rejects_non_positive_full_incremental_uplift(self):
        import src.business as business

        zero_uplift_segments = pd.DataFrame(
            {
                "cate": [0.0, 0.0, 0.0, 0.0],
                "baseline_prob": [0.01, 0.01, 0.01, 0.01],
                "segment": ["Persuadables", "Sure Things", "Lost Causes", "Sleeping Dogs"],
            }
        )
        y = pd.Series([0, 1, 0, 1])
        t = pd.Series([0, 1, 0, 1])

        with pytest.raises(ValueError, match="Full targeting incremental uplift must be > 0"):
            business.simulate_roi(zero_uplift_segments, Y=y, T=t)
