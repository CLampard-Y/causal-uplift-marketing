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
        with pytest.raises(ValueError, match="baseline_prob outside \[0, 1\]"):
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
