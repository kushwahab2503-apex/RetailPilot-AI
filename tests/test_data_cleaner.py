import pytest
import pandas as pd
import numpy as np
from backend.data_cleaner import apply_cleaning, generate_cleaning_recommendations

def test_original_preserved():
    df = pd.DataFrame({"Quantity": [-5, 10]})
    mem_addr = id(df)
    res = apply_cleaning(df, {"remove_invalid_quantity": True})
    cleaned = res["cleaned_dataframe"]
    
    # Original is untouched
    assert len(df) == 2
    assert id(cleaned) != mem_addr
    assert len(cleaned) == 1

def test_exact_duplicate_works():
    df = pd.DataFrame({"OrderID": ["O1", "O1"], "Item": ["A", "A"]})
    res = apply_cleaning(df, {"remove_exact_duplicates": True})
    assert len(res["cleaned_dataframe"]) == 1

def test_repeated_order_id_preserved_when_no_exact_duplicates():
    df = pd.DataFrame({"OrderID": ["O1", "O1"], "Item": ["A", "B"]})
    res = apply_cleaning(df, {"remove_exact_duplicates": True})
    assert len(res["cleaned_dataframe"]) == 2

def test_whitespace_normalization():
    df = pd.DataFrame({"Category": ["  shoes  ", "", "  ", "hat"]})
    res = apply_cleaning(df, {"normalize_whitespace": True})
    c = res["cleaned_dataframe"]
    assert c["Category"].iloc[0] == "shoes"
    assert pd.isna(c["Category"].iloc[1])
    assert pd.isna(c["Category"].iloc[2])

def test_date_conversion():
    df = pd.DataFrame({"OrderDate": ["2025-01-01", "NotADate"]})
    res = apply_cleaning(df, {"convert_dates": True})
    c = res["cleaned_dataframe"]
    assert pd.notna(c["OrderDate"].iloc[0])
    assert pd.isna(c["OrderDate"].iloc[1])
    assert len(res["warnings"]) == 1

def test_numeric_conversion():
    df = pd.DataFrame({"UnitPrice": ["10.5", "bad"], "Quantity": [5, "worse"]})
    res = apply_cleaning(df, {"convert_numerics": True})
    c = res["cleaned_dataframe"]
    assert c["UnitPrice"].iloc[0] == 10.5
    assert pd.isna(c["UnitPrice"].iloc[1])
    assert pd.isna(c["Quantity"].iloc[1])
    assert len(res["warnings"]) == 2

def test_destructive_row_removals():
    df = pd.DataFrame({
        "OrderID": ["O1", "O2", np.nan, "O4"],
        "UnitPrice": [10.0, -5.0, 10.0, 10.0],
        "Quantity": [5, 5, 5, 0]
    })
    res = apply_cleaning(df, {
        "remove_invalid_quantity": True, 
        "remove_negative_price": True, 
        "remove_blank_order_id": True
    })
    c = res["cleaned_dataframe"]
    assert len(c) == 1
    assert c["OrderID"].iloc[0] == "O1"

def test_combined_summary_metrics():
    df = pd.DataFrame({
        "OrderID": ["O1", "O2", "O2", "O3"],
        "Quantity": [10, -5, -5, 10] # Contains exact duplicate AND invalid business rule
    })
    # Count missing initially: 0
    res = apply_cleaning(df, {"remove_exact_duplicates": True, "remove_invalid_quantity": True})
    s = res["summary"]
    
    # original = 4 rows. O2 duplicate is removed (1). O2 negative qty is removed (1). Leaving O1 and O3.
    assert s["raw_rows"] == 4
    assert s["clean_rows"] == 2
    assert s["rows_removed"] == 2
    assert s["exact_duplicates_after"] == 0
    
def test_recommendation_generation():
    val_mock = {
        "summary": {"exact_duplicates": 5},
        "warnings": ["OrderDate formatting mismatch detected in whitespace"],
        "business_rule_results": {"invalid_quantity": 2},
        "column_results": {}
    }
    recs = generate_cleaning_recommendations(val_mock)
    keys = [r["action_key"] for r in recs]
    assert "remove_exact_duplicates" in keys
    assert "normalize_whitespace" in keys
    assert "convert_dates" in keys
    assert "remove_invalid_quantity" in keys
