import pandas as pd
import numpy as np
from typing import Dict, Any

REQUIRED_COLUMNS = [
    "OrderID", "OrderDate", "ProductID", "ProductName", 
    "Category", "Quantity", "UnitPrice"
]

MODULE_DEPENDENT_COLUMNS = {
    "CustomerID": "customer_analytics",
    "UnitCost": "profit_analytics"
}

def validate_dataset(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Validate the provided dataframe against the RetailPilot AI schema.
    Returns a structured validation result dict.
    """
    result = {
        "is_valid": True,
        "errors": [],
        "warnings": [],
        "summary": {},
        "missing_required_columns": [],
        "available_modules": {
            "core_dashboard": True,
            "product_analytics": True,
            "customer_analytics": False,
            "profit_analytics": False
        },
        "column_results": {},
        "business_rule_results": {},
        "data_quality_score": 100,
        "quality_band": "Good"
    }
    
    # 1. Schema Validation
    missing_req = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_req:
        result["missing_required_columns"] = missing_req
        result["is_valid"] = False
        result["errors"].append(f"Missing required columns: {', '.join(missing_req)}")
        result["available_modules"]["core_dashboard"] = False
        result["available_modules"]["product_analytics"] = False
        
    for col, module in MODULE_DEPENDENT_COLUMNS.items():
        if col in df.columns:
            result["available_modules"][module] = True
        else:
            result["warnings"].append(f"Missing '{col}', {module.replace('_', ' ')} will be unavailable.")

    if not result["is_valid"]:
        # If schema is fundamentally broken, skip deeper checks for score
        result["data_quality_score"] = 0
        result["quality_band"] = "Critical"
        return result

    # 2. Data Type Validation
    type_issues = []
    
    if "OrderDate" in df.columns:
        parsed_dates = pd.to_datetime(df["OrderDate"], errors='coerce')
        unparseable_dates = parsed_dates.isna().sum() - df["OrderDate"].isna().sum()
        if unparseable_dates > 0:
            type_issues.append(f"OrderDate has {unparseable_dates} unparseable values.")
            
    numeric_cols_to_check = ["Quantity", "UnitPrice"]
    optional_numerics = ["UnitCost", "DiscountPct", "StockAvailable"]
    numeric_cols_to_check.extend([c for c in optional_numerics if c in df.columns])

    for col in numeric_cols_to_check:
        numeric_vals = pd.to_numeric(df[col], errors='coerce')
        unparseables = numeric_vals.isna().sum() - df[col].isna().sum()
        if unparseables > 0:
            type_issues.append(f"{col} has {unparseables} values that cannot be converted to numbers.")
            
    if type_issues:
        result["warnings"].extend(type_issues)

    # 3. Missing Value Analysis
    total_cells = df.shape[0] * df.shape[1]
    total_missing = int(df.isna().sum().sum())
    rows_with_missing = int(df.isna().any(axis=1).sum())
    
    for col in df.columns:
        missing_count = int(df[col].isna().sum())
        missing_pct = (missing_count / df.shape[0] * 100) if df.shape[0] > 0 else 0
        if missing_count > 0:
            result["column_results"][col] = {
                "missing_count": missing_count,
                "missing_pct": round(missing_pct, 2)
            }

    # 4. Duplicate Analysis
    exact_duplicates = int(df.duplicated().sum())
    
    repeated_orders = 0
    if "OrderID" in df.columns:
        repeated_orders = int(df.duplicated(subset=["OrderID"], keep=False).sum())
        
    result["summary"] = {
        "exact_duplicates": exact_duplicates,
        "repeated_order_ids": repeated_orders,
        "total_missing": total_missing,
        "rows_with_missing": rows_with_missing,
        "total_rows": df.shape[0],
        "total_columns": df.shape[1]
    }
    
    # 5. Business Rule Validation
    biz_rules = {}
    
    if "Quantity" in df.columns:
        numeric_q = pd.to_numeric(df["Quantity"], errors='coerce')
        invalid_q = int((numeric_q <= 0).sum())
        if invalid_q > 0:
            biz_rules["invalid_quantity"] = invalid_q
            result["warnings"].append(f"{invalid_q} rows have Quantity <= 0.")
            
    if "UnitPrice" in df.columns:
        numeric_p = pd.to_numeric(df["UnitPrice"], errors='coerce')
        invalid_p = int((numeric_p < 0).sum())
        if invalid_p > 0:
            biz_rules["invalid_price"] = invalid_p
            result["warnings"].append(f"{invalid_p} rows have UnitPrice < 0.")

    if "UnitCost" in df.columns:
        numeric_c = pd.to_numeric(df["UnitCost"], errors='coerce')
        invalid_c = int((numeric_c < 0).sum())
        if invalid_c > 0:
            biz_rules["invalid_cost"] = invalid_c
            result["warnings"].append(f"{invalid_c} rows have UnitCost < 0.")
            
    if "DiscountPct" in df.columns:
        numeric_d = pd.to_numeric(df["DiscountPct"], errors='coerce')
        invalid_d = int(((numeric_d < 0) | (numeric_d > 100)).sum())
        if invalid_d > 0:
            biz_rules["invalid_discount"] = invalid_d
            result["warnings"].append(f"{invalid_d} rows have DiscountPct outside 0-100 range.")

    if "OrderID" in df.columns:
        # Treat empty strings as missing
        blank_orders = int(df["OrderID"].replace(r'^\s*$', np.nan, regex=True).isna().sum())
        if blank_orders > 0:
            biz_rules["blank_order_id"] = blank_orders
            result["warnings"].append(f"{blank_orders} rows have empty OrderID.")

    if "ProductID" in df.columns:
        blank_products = int(df["ProductID"].replace(r'^\s*$', np.nan, regex=True).isna().sum())
        if blank_products > 0:
            biz_rules["blank_product_id"] = blank_products
            result["warnings"].append(f"{blank_products} rows have empty ProductID.")

    result["business_rule_results"] = biz_rules

    # 6. Data Quality Score Calculus (0 - 100)
    score = 100
    
    missing_pct = total_missing / total_cells if total_cells > 0 else 0
    score -= min(30, missing_pct * 100) 
    
    dup_pct = exact_duplicates / df.shape[0] if df.shape[0] > 0 else 0
    score -= min(15, dup_pct * 100)
    
    if type_issues:
        score -= min(15, len(type_issues) * 5)
        
    biz_violators = sum(biz_rules.values())
    biz_violator_pct = biz_violators / df.shape[0] if df.shape[0] > 0 else 0
    score -= min(30, biz_violator_pct * 100)
    
    if result["errors"]:
        score -= 20
        
    score = max(0, int(score))
    result["data_quality_score"] = score
    
    if score >= 90:
        result["quality_band"] = "Good"
    elif score >= 70:
        result["quality_band"] = "Attention Required"
    else:
        result["quality_band"] = "Critical"
        
    return result
