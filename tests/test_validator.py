import pytest
import pandas as pd
from backend.validator import validate_dataset

def test_valid_minimal_dataset():
    """Test valid minimal dataset."""
    df = pd.DataFrame({
        "OrderID": ["O1", "O2"],
        "OrderDate": ["2025-01-01", "2025-01-02"],
        "ProductID": ["P1", "P1"],
        "ProductName": ["Lap", "Lap"],
        "Category": ["cat", "cat"],
        "Quantity": [1, 2],
        "UnitPrice": [10.0, 10.0]
    })
    res = validate_dataset(df)
    assert res["is_valid"] is True
    assert res["data_quality_score"] == 100
    assert res["quality_band"] == "Good"
    assert len(res["errors"]) == 0

def test_missing_required_column():
    """Test missing required column."""
    df = pd.DataFrame({"OrderID": ["O1"]}) # Missing almost everything
    res = validate_dataset(df)
    assert res["is_valid"] is False
    assert len(res["missing_required_columns"]) > 0
    assert res["data_quality_score"] == 0
    assert res["quality_band"] == "Critical"

def test_missing_customer_id_core_dataset():
    """Test missing CustomerID does not invalidate core dataset."""
    df = pd.DataFrame({
        "OrderID": ["O1"], "OrderDate": ["2025-01-01"],
        "ProductID": ["P1"], "ProductName": ["Lap"],
        "Category": ["cat"], "Quantity": [1], "UnitPrice": [10.0]
    })
    res = validate_dataset(df)
    assert res["is_valid"] is True
    assert res["available_modules"]["core_dashboard"] is True
    assert res["available_modules"]["customer_analytics"] is False
    assert any("CustomerID" in w for w in res["warnings"])

def test_invalid_dates():
    """Test invalid dates."""
    df = pd.DataFrame({
        "OrderID": ["O1"], "OrderDate": ["NotADate"],
        "ProductID": ["P1"], "ProductName": ["Lap"],
        "Category": ["cat"], "Quantity": [1], "UnitPrice": [10.0]
    })
    res = validate_dataset(df)
    assert res["is_valid"] is True
    assert any("OrderDate" in str(w) for w in res["warnings"])
    assert res["data_quality_score"] < 100

def test_invalid_numeric_values():
    """Test invalid numeric values."""
    df = pd.DataFrame({
        "OrderID": ["O1"], "OrderDate": ["2025-01-01"],
        "ProductID": ["P1"], "ProductName": ["Lap"],
        "Category": ["cat"], "Quantity": ["bad"], "UnitPrice": [10.0]
    })
    res = validate_dataset(df)
    assert res["is_valid"] is True
    assert any("Quantity" in str(w) for w in res["warnings"])
    assert res["data_quality_score"] < 100

def test_exact_duplicate_rows():
    """Test exact duplicate rows."""
    df = pd.DataFrame({
        "OrderID": ["O1", "O1"], "OrderDate": ["2025-01-01", "2025-01-01"],
        "ProductID": ["P1", "P1"], "ProductName": ["Lap", "Lap"],
        "Category": ["cat", "cat"], "Quantity": [1, 1], "UnitPrice": [10.0, 10.0]
    })
    res = validate_dataset(df)
    assert res["summary"]["exact_duplicates"] == 1

def test_repeated_order_id_distinction():
    """Test repeated OrderID distinction."""
    df = pd.DataFrame({
        "OrderID": ["O1", "O1"], "OrderDate": ["2025-01-01", "2025-01-01"],
        "ProductID": ["P1", "P2"], "ProductName": ["Lap", "Mouse"],
        "Category": ["cat", "acc"], "Quantity": [1, 2], "UnitPrice": [10.0, 5.0]
    })
    res = validate_dataset(df)
    assert res["summary"]["exact_duplicates"] == 0
    assert res["summary"]["repeated_order_ids"] == 2

def test_business_rule_violations():
    """Test business rule violations."""
    df = pd.DataFrame({
        "OrderID": ["O1"], "OrderDate": ["2025-01-01"],
        "ProductID": ["P1"], "ProductName": ["Lap"],
        "Category": ["cat"], "Quantity": [-5], "UnitPrice": [-10.0]
    })
    res = validate_dataset(df)
    assert "invalid_quantity" in res["business_rule_results"]
    assert "invalid_price" in res["business_rule_results"]
    assert any("Quantity <= 0" in w for w in res["warnings"])

def test_data_quality_score_bounded():
    """Test Data Quality Score is bounded between 0 and 100 on an extremely bad dataset."""
    df = pd.DataFrame({
        "OrderID": ["", ""], "OrderDate": ["NotDate", "BadDate"],
        "ProductID": ["", ""], "ProductName": ["", ""],
        "Category": ["", ""], "Quantity": [-1, "bad"], "UnitPrice": [-5, "bad"],
        "UnitCost": [-1, "bad"], "DiscountPct": [-1, 200]
    })
    res = validate_dataset(df)
    assert res["data_quality_score"] >= 0
    assert res["data_quality_score"] <= 100
