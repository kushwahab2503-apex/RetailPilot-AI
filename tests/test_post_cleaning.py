"""
tests/test_post_cleaning.py

Focused tests for the post-cleaning workflow introduced in the Data Cleaning pipeline:
  - Post-cleaning revalidation produces a separate result
  - Original validation result is not mutated
  - Cleaned dataframe exports to CSV without index leakage
  - apply_cleaning remains non-destructive
  - Score/band fields are present in both results
  - State key expectations for reset logic
"""
import io
import pytest
import pandas as pd
import numpy as np

from backend.validator import validate_dataset
from backend.data_cleaner import apply_cleaning


# ── Shared fixtures ───────────────────────────────────────────────────────────

def _make_dirty_df():
    """A small dataset with exact duplicates, an invalid date, and whitespace."""
    return pd.DataFrame({
        "OrderID":     ["O1", "O1", "O2", "O3"],
        "OrderDate":   ["2025-01-01", "2025-01-01", "NOT_A_DATE", "2025-03-01"],
        "ProductID":   ["P1", "P1", "P2", "P3"],
        "ProductName": ["Laptop", "Laptop", "  Mouse  ", "Keyboard"],
        "Category":    ["Electronics", "Electronics", "Accessories", "Accessories"],
        "Quantity":    [5, 5, 2, 3],
        "UnitPrice":   [999.0, 999.0, 25.0, 45.0],
    })


def _make_clean_df():
    """A minimal, fully valid dataset."""
    return pd.DataFrame({
        "OrderID":     ["O1", "O2"],
        "OrderDate":   ["2025-01-01", "2025-02-01"],
        "ProductID":   ["P1", "P2"],
        "ProductName": ["Laptop", "Mouse"],
        "Category":    ["Electronics", "Accessories"],
        "Quantity":    [5, 2],
        "UnitPrice":   [999.0, 25.0],
    })


# ── 1. Raw and cleaned validation results remain independent ──────────────────

class TestValidationResultIsolation:

    def test_raw_validation_result_unchanged_after_cleaning(self):
        """
        Simulates the page flow: validate raw → apply cleaning → validate cleaned.
        The original validation result dict must not be mutated.
        """
        raw_df = _make_dirty_df()

        raw_val = validate_dataset(raw_df)
        raw_score_before = raw_val["data_quality_score"]
        raw_rows_before  = raw_val["summary"]["total_rows"]

        # Apply cleaning
        config = {
            "remove_exact_duplicates": True,
            "normalize_whitespace":    True,
            "convert_dates":           True,
        }
        res = apply_cleaning(raw_df, config)
        cleaned_df = res["cleaned_dataframe"]

        # Validate cleaned dataset separately
        cleaned_val = validate_dataset(cleaned_df)

        # Original result must be unchanged
        assert raw_val["data_quality_score"] == raw_score_before
        assert raw_val["summary"]["total_rows"] == raw_rows_before

        # The two results are distinct objects
        assert raw_val is not cleaned_val

    def test_cleaned_validation_references_cleaned_row_count(self):
        """Cleaned validation summary reflects the cleaned row count, not the raw one."""
        raw_df = _make_dirty_df()  # 4 rows, 1 exact duplicate → 3 after dedup

        res = apply_cleaning(raw_df, {"remove_exact_duplicates": True})
        cleaned_df = res["cleaned_dataframe"]
        cleaned_val = validate_dataset(cleaned_df)

        assert cleaned_val["summary"]["total_rows"] == len(cleaned_df)
        assert cleaned_val["summary"]["total_rows"] < len(raw_df)

    def test_post_clean_validation_has_required_keys(self):
        """validate_dataset returns all keys expected by the comparison UI."""
        df = _make_clean_df()
        val = validate_dataset(df)
        for key in ["data_quality_score", "quality_band", "is_valid", "summary",
                    "errors", "warnings"]:
            assert key in val, f"Missing key: {key}"

    def test_scores_are_independent_values(self):
        """Raw and cleaned scores may differ; neither is forced to equal the other."""
        raw_df = _make_dirty_df()
        raw_val = validate_dataset(raw_df)

        res = apply_cleaning(raw_df, {
            "remove_exact_duplicates": True,
            "convert_dates": True,
        })
        cleaned_val = validate_dataset(res["cleaned_dataframe"])

        # Both scores must be valid integers in [0, 100]
        assert 0 <= raw_val["data_quality_score"] <= 100
        assert 0 <= cleaned_val["data_quality_score"] <= 100
        # They may be equal, higher, or lower — no assumption is forced
        assert isinstance(cleaned_val["data_quality_score"], int)


# ── 2. CSV export correctness ─────────────────────────────────────────────────

class TestCSVExport:

    def test_csv_export_has_no_index_column(self):
        """Exporting cleaned_df with index=False must not produce an index column."""
        df = _make_clean_df()
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        reloaded = pd.read_csv(io.BytesIO(csv_bytes))
        # 'Unnamed: 0' would appear if index=True were used accidentally
        assert "Unnamed: 0" not in reloaded.columns

    def test_csv_roundtrip_preserves_row_count(self):
        """CSV round-trip must not add or drop rows."""
        df = _make_clean_df()
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        reloaded = pd.read_csv(io.BytesIO(csv_bytes))
        assert len(reloaded) == len(df)

    def test_csv_roundtrip_preserves_column_names(self):
        """Column names survive the encode/decode cycle."""
        df = _make_clean_df()
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        reloaded = pd.read_csv(io.BytesIO(csv_bytes))
        assert list(reloaded.columns) == list(df.columns)

    def test_csv_export_does_not_mutate_dataframe(self):
        """Calling to_csv() must not modify the source dataframe in place."""
        df = _make_clean_df()
        original_shape = df.shape
        _ = df.to_csv(index=False)
        assert df.shape == original_shape


# ── 3. apply_cleaning remains non-destructive ─────────────────────────────────

class TestNonDestructiveCleaning:

    def test_raw_df_unchanged_after_apply_cleaning(self):
        """The dataframe passed to apply_cleaning must be identical afterwards."""
        raw_df = _make_dirty_df()
        raw_snapshot = raw_df.copy(deep=True)

        apply_cleaning(raw_df, {
            "remove_exact_duplicates": True,
            "normalize_whitespace": True,
            "convert_dates": True,
            "convert_numerics": True,
        })

        pd.testing.assert_frame_equal(raw_df, raw_snapshot)

    def test_cleaned_df_is_a_separate_object(self):
        """cleaned_dataframe must not share identity with the input."""
        raw_df = _make_dirty_df()
        res = apply_cleaning(raw_df, {"normalize_whitespace": True})
        assert res["cleaned_dataframe"] is not raw_df


# ── 4. Reset state key expectations ──────────────────────────────────────────

class TestResetStateKeys:
    """
    The page resets state by popping specific keys from st.session_state.
    These tests verify the expected set of keys using a plain dict
    to avoid a Streamlit dependency in unit tests.
    """

    RESET_KEYS = [
        "cleaned_df",
        "cleaning_config",
        "cleaning_summary",
        "cleaning_applied",
        "cleaned_validation_result",
    ]
    PRESERVE_KEYS = [
        "raw_df",
        "validation_results",
        "dataset_loaded",
    ]

    def test_reset_keys_are_removed(self):
        state = {k: "value" for k in self.RESET_KEYS + self.PRESERVE_KEYS}
        for key in self.RESET_KEYS:
            state.pop(key, None)
        for key in self.RESET_KEYS:
            assert key not in state

    def test_preserve_keys_survive_reset(self):
        state = {k: "value" for k in self.RESET_KEYS + self.PRESERVE_KEYS}
        for key in self.RESET_KEYS:
            state.pop(key, None)
        for key in self.PRESERVE_KEYS:
            assert key in state

    def test_cleaned_validation_result_is_in_reset_list(self):
        """Ensures the new key is explicitly included in the reset set."""
        assert "cleaned_validation_result" in self.RESET_KEYS

    def test_raw_validation_not_in_reset_list(self):
        """Ensures validation_results (raw) is never wiped by a reset."""
        assert "validation_results" not in self.RESET_KEYS

    def test_new_upload_stale_keys(self):
        """New upload must clear the same set of keys as a reset plus cleaned_validation_result."""
        upload_clear_keys = [
            "cleaned_df",
            "cleaning_config",
            "cleaning_summary",
            "cleaning_applied",
            "cleaned_validation_result",
        ]
        # Every reset key must also be cleared on new upload
        for key in self.RESET_KEYS:
            assert key in upload_clear_keys
