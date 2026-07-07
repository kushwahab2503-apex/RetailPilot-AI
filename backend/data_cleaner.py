import pandas as pd
import numpy as np

def generate_cleaning_recommendations(val_result):
    """
    Generate deterministic cleaning recommendations based on raw validation results.
    """
    recs = []
    
    # Duplicates
    if val_result["summary"].get("exact_duplicates", 0) > 0:
        recs.append({
            "action_key": "remove_exact_duplicates",
            "title": "Remove Exact Duplicates",
            "explanation": "Identical rows detected. This action removes fully exact duplicates while preserving valid repeated orders.",
            "affected_count": val_result["summary"]["exact_duplicates"],
            "severity": "medium",
            "default": True
        })
        
    # Strings analysis (we map it globally for simplicity if there are any whitespace warnings in the dataset)
    has_whitespace_warnings = any("whitespace" in str(w).lower() for w in val_result["warnings"])
    if has_whitespace_warnings:
        recs.append({
            "action_key": "normalize_whitespace",
            "title": "Normalize Whitespace",
            "explanation": "Trims leading/trailing spaces and converts purely blank strings to proper missing values natively.",
            "affected_count": "Multiple columns",
            "severity": "low",
            "default": True
        })
        
    # Dates
    invalid_date_warnings = any("OrderDate" in str(w) for w in val_result["warnings"])
    if invalid_date_warnings:
        recs.append({
            "action_key": "convert_dates",
            "title": "Fix Date Formatting",
            "explanation": "Validates dates and safely coerces completely broken dates into missing values.",
            "affected_count": "OrderDate",
            "severity": "medium",
            "default": True
        })
        
    # Numerics
    numeric_columns = ["Quantity", "UnitPrice", "DiscountPct", "UnitCost", "StockAvailable"]
    has_num_warn = any(any(col in str(w) for w in val_result["warnings"]) for col in numeric_columns)
    if has_num_warn:
        recs.append({
            "action_key": "convert_numerics",
            "title": "Coerce Invalid Numerics",
            "explanation": "Forces numeric types. Unsalvageable text within numeric columns will become missing (NaN).",
            "affected_count": "Numeric columns",
            "severity": "medium",
            "default": True
        })
        
    # Business Rules (Critical Destructive Row Actions) - default: False
    b_rules = val_result["business_rule_results"]
    if b_rules.get("invalid_quantity", 0) > 0:
        recs.append({
            "action_key": "remove_invalid_quantity",
            "title": "Remove Quantity <= 0 Rows",
            "explanation": "Critical business rule violation.",
            "affected_count": b_rules["invalid_quantity"],
            "severity": "critical",
            "default": False
        })
        
    if b_rules.get("invalid_price", 0) > 0:
        recs.append({
            "action_key": "remove_negative_price",
            "title": "Remove Negative Price Rows",
            "explanation": "Critical business rule violation.",
            "affected_count": b_rules["invalid_price"],
            "severity": "critical",
            "default": False
        })
        
    if b_rules.get("blank_order_id", 0) > 0 or val_result["column_results"].get("OrderID", {}).get("missing_count", 0) > 0:
        recs.append({
            "action_key": "remove_blank_order_id",
            "title": "Remove Missing Order IDs",
            "explanation": "Removes transactions missing the core operational identifier.",
            "affected_count": "Variable",
            "severity": "critical",
            "default": False
        })
        
    return recs


def apply_cleaning(raw_df: pd.DataFrame, config: dict) -> dict:
    """
    Executes selected deterministic operations against a copy of the dataframe.
    """
    df = raw_df.copy()
    
    actions_applied = []
    warnings = []
    
    # 1. Whitespace String Normalization
    if config.get("normalize_whitespace"):
        string_cols = df.select_dtypes(include=['object', 'string']).columns
        for col in string_cols:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace({'': np.nan, 'nan': np.nan, 'None': np.nan})
        actions_applied.append("normalize_whitespace")
        
    # 2. Date Conversions
    if config.get("convert_dates") and "OrderDate" in df.columns:
        original_nans = df["OrderDate"].isna().sum()
        df["OrderDate"] = pd.to_datetime(df["OrderDate"], errors="coerce")
        new_nans = df["OrderDate"].isna().sum()
        
        diff = new_nans - original_nans
        if diff > 0:
            warnings.append(f"{diff} date cells were irreversibly corrupted and became missing.")
        actions_applied.append("convert_dates")
        
    # 3. Numeric Conversions
    if config.get("convert_numerics"):
        numeric_targets = ["Quantity", "UnitPrice", "DiscountPct", "UnitCost", "StockAvailable"]
        for col in numeric_targets:
            if col in df.columns:
                original_nans = df[col].isna().sum()
                df[col] = pd.to_numeric(df[col], errors="coerce")
                diff = df[col].isna().sum() - original_nans
                if diff > 0:
                    warnings.append(f"{diff} invalid text values in {col} became missing.")
        actions_applied.append("convert_numerics")
        
    # 4. Critical Business Removals
    if config.get("remove_invalid_quantity") and "Quantity" in df.columns:
        df = df[df["Quantity"] > 0]
        actions_applied.append("remove_invalid_quantity")
        
    if config.get("remove_negative_price") and "UnitPrice" in df.columns:
        df = df[df["UnitPrice"] >= 0]
        actions_applied.append("remove_negative_price")
        
    if config.get("remove_blank_order_id") and "OrderID" in df.columns:
        df = df.dropna(subset=["OrderID"])
        actions_applied.append("remove_blank_order_id")
        
    # 5. Exact Duplicates
    if config.get("remove_exact_duplicates"):
        initial_count = len(df)
        df = df.drop_duplicates(keep="first")
        removed = initial_count - len(df)
        actions_applied.append("remove_exact_duplicates")
        
    # Reset index cleanly after row alterations
    df = df.reset_index(drop=True)

    summary = {
        "raw_rows": len(raw_df),
        "clean_rows": len(df),
        "rows_removed": len(raw_df) - len(df),
        "raw_missing_cells": int(raw_df.isna().sum().sum()),
        "clean_missing_cells": int(df.isna().sum().sum()),
        "exact_duplicates_after": int(df.duplicated().sum())
    }

    return {
        "success": True,
        "cleaned_dataframe": df,
        "summary": summary,
        "actions_applied": actions_applied,
        "warnings": warnings,
        "error": None
    }
