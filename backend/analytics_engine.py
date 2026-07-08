import pandas as pd
import numpy as np
import math
from typing import Dict, Any, Tuple, Optional, List

def prepare_analytics_dataset(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Prepares a raw or cleaned dataset for analytical usage.
    Creates a defensive copy, checks schema structure, normalizes types,
    applies strict operational row exclusion rules, and derives revenue.

    Eligibility / Exclusions criteria:
      - OrderID: must not be null/NaN or empty/whitespace string.
      - OrderDate: must be parseable/convertible to non-NaT datetime.
      - Quantity: must be a positive number (> 0) and convertible to numeric.
      - UnitPrice: must be a non-negative number (>= 0) and convertible to numeric.

    Returns:
        (prepared_df, metadata)
    """
    if df is None:
        return pd.DataFrame(), {
            "row_count_analyzed": 0,
            "valid_row_count": 0,
            "excluded_row_count": 0,
            "exclusions": {},
            "revenue_basis": "Gross Revenue"
        }

    # Defensive copy
    work_df = df.copy()
    row_count_analyzed = len(work_df)

    # Required columns check
    required_cols = ["OrderID", "OrderDate", "Quantity", "UnitPrice"]
    missing_required = [col for col in required_cols if col not in work_df.columns]
    
    if missing_required or work_df.empty:
        # Return empty dataframe with column structures to survive downstream tasks
        for col in required_cols:
            if col not in work_df.columns:
                work_df[col] = pd.Series(dtype=object)
        work_df["_Revenue"] = pd.Series(dtype=float)
        
        return work_df.iloc[0:0].copy(), {
            "row_count_analyzed": row_count_analyzed,
            "valid_row_count": 0,
            "excluded_row_count": row_count_analyzed,
            "exclusions": {
                "missing_required_columns": len(missing_required),
                "missing_or_invalid_order_id": row_count_analyzed if "OrderID" not in df.columns else 0,
                "missing_or_invalid_order_date": row_count_analyzed if "OrderDate" not in df.columns else 0,
                "invalid_quantity": row_count_analyzed if "Quantity" not in df.columns else 0,
                "invalid_price": row_count_analyzed if "UnitPrice" not in df.columns else 0
            },
            "revenue_basis": "Gross Revenue",
            "invalid_discount_fallback_count": 0
        }
    
    # Track logical masks for validation
    # 1. OrderID
    order_ids_str = work_df["OrderID"].astype(str).str.strip()
    is_order_id_invalid = (
        work_df["OrderID"].isna() | 
        (order_ids_str == "") | 
        (order_ids_str.str.lower() == "nan") | 
        (order_ids_str.str.lower() == "none")
    )

    # 2. OrderDate
    parsed_dates = pd.to_datetime(work_df["OrderDate"], errors='coerce')
    is_date_invalid = parsed_dates.isna()

    # 3. Quantity
    numeric_q = pd.to_numeric(work_df["Quantity"], errors='coerce')
    is_quantity_invalid = numeric_q.isna() | (numeric_q <= 0)

    # 4. UnitPrice
    numeric_p = pd.to_numeric(work_df["UnitPrice"], errors='coerce')
    is_price_invalid = numeric_p.isna() | (numeric_p < 0)

    # Calculate exact exclusions
    # A row is excluded if ANY of the core rules are violated
    excluded_mask = is_order_id_invalid | is_date_invalid | is_quantity_invalid | is_price_invalid
    
    # Calculate counts per exclusion categories for the report metadata
    missing_order_ids = int(is_order_id_invalid.sum())
    missing_or_invalid_dates = int(is_date_invalid.sum())
    invalid_quantities = int(is_quantity_invalid.sum())
    invalid_prices = int(is_price_invalid.sum())
    
    total_excluded = int(excluded_mask.sum())
    valid_row_count = row_count_analyzed - total_excluded

    # Retrieve only eligible rows for computation
    prepared_df = work_df[~excluded_mask].copy()

    # Enforce data types on prepared dataframe to ensure mathematical operations are robust
    if len(prepared_df) > 0:
        prepared_df["OrderID"] = prepared_df["OrderID"].astype(str).str.strip()
        prepared_df["OrderDate"] = pd.to_datetime(prepared_df["OrderDate"], errors='coerce')
        prepared_df["Quantity"] = pd.to_numeric(prepared_df["Quantity"], errors='coerce')
        prepared_df["UnitPrice"] = pd.to_numeric(prepared_df["UnitPrice"], errors='coerce')

        # Safely parse optional ones if available
        if "UnitCost" in prepared_df.columns:
            prepared_df["UnitCost"] = pd.to_numeric(prepared_df["UnitCost"], errors='coerce')
        if "DiscountPct" in prepared_df.columns:
            prepared_df["DiscountPct"] = pd.to_numeric(prepared_df["DiscountPct"], errors='coerce')

    # Derived revenue calculations
    revenue_basis = "Gross Revenue"
    invalid_discount_fallback_count = 0

    if "DiscountPct" in prepared_df.columns:
        revenue_basis = "Net Revenue"
        
        # Calculate net revenue per row
        quantities = prepared_df["Quantity"].values
        unit_prices = prepared_df["UnitPrice"].values
        discount_pcts = prepared_df["DiscountPct"].values
        
        calculated_revenues = []
        for q, p, d in zip(quantities, unit_prices, discount_pcts):
            # Check if discount percentage is valid (non-null and inside [0, 100])
            if pd.isna(d) or not (0 <= d <= 100):
                # Fallback to Gross Revenue for this specific row
                calculated_revenues.append(float(q * p))
                invalid_discount_fallback_count += 1
            else:
                calculated_revenues.append(float(q * p * (1.0 - (d / 100.0))))
                
        prepared_df["_Revenue"] = calculated_revenues
    else:
        prepared_df["_Revenue"] = prepared_df["Quantity"] * prepared_df["UnitPrice"]

    metadata = {
        "row_count_analyzed": row_count_analyzed,
        "valid_row_count": valid_row_count,
        "excluded_row_count": total_excluded,
        "exclusions": {
            "missing_or_invalid_order_id": missing_order_ids,
            "missing_or_invalid_order_date": missing_or_invalid_dates,
            "invalid_quantity": invalid_quantities,
            "invalid_price": invalid_prices
        },
        "revenue_basis": revenue_basis,
        "invalid_discount_fallback_count": invalid_discount_fallback_count
    }

    return prepared_df, metadata


def calculate_core_kpis(df: pd.DataFrame, revenue_basis: str) -> Dict[str, Any]:
    """
    Calculate high-level KPI operations:
      - Total Revenue
      - Total Orders (unique OrderID list)
      - Units Sold (sum of valid Quantity)
      - Average Order Value (total_revenue / total_orders)
    """
    if df.empty:
        return {
            "total_revenue": 0.0,
            "total_orders": 0,
            "units_sold": 0,
            "average_order_value": 0.0,
            "date_range": "N/A",
            "row_count_analyzed": 0,
            "revenue_basis": revenue_basis
        }

    total_revenue = float(df["_Revenue"].sum())
    total_orders = int(df["OrderID"].nunique())
    units_sold = int(df["Quantity"].sum())
    
    if total_orders > 0:
        aov = total_revenue / total_orders
    else:
        aov = 0.0
        
    # Find min and max OrderDate
    min_date = df["OrderDate"].min()
    max_date = df["OrderDate"].max()
    
    if pd.isna(min_date) or pd.isna(max_date):
        date_range_str = "N/A"
    else:
        date_range_str = f"{min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}"
        
    return {
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "units_sold": units_sold,
        "average_order_value": aov,
        "date_range": date_range_str,
        "row_count_analyzed": len(df),
        "revenue_basis": revenue_basis
    }


def aggregate_time_series(df: pd.DataFrame, frequency: str) -> pd.DataFrame:
    """
    Aggregate Revenue, unique Orders, and Units chronologically at a chosen frequency:
      - Daily
      - Weekly (Monday of the week)
      - Monthly (First day of the month)
    """
    expected_cols = ["Date", "Revenue", "Orders", "Units"]
    if df.empty:
        return pd.DataFrame(columns=expected_cols)

    # Work on defensive copy
    work_df = df.copy()

    # Determine grouping column based on frequency
    if frequency == "Weekly":
        work_df["period_date"] = work_df["OrderDate"].dt.to_period('W').dt.to_timestamp()
    elif frequency == "Monthly":
        work_df["period_date"] = work_df["OrderDate"].dt.to_period('M').dt.to_timestamp()
    else: # Default is Daily
        work_df["period_date"] = work_df["OrderDate"].dt.normalize()

    # Group by the aggregated date
    grouped = work_df.groupby("period_date").agg(
        Revenue=("_Revenue", "sum"),
        Units=("Quantity", "sum"),
        Orders=("OrderID", "nunique")
    ).reset_index()

    # Rename grouping column and sorting chronologically
    grouped = grouped.rename(columns={"period_date": "Date"})
    grouped = grouped.sort_values("Date").reset_index(drop=True)
    
    return grouped[expected_cols]


def calculate_category_performance(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes performance broken down by product Category.
    Missing categories are bucketed under "Unknown".
    Columns: Category, Revenue, Orders, Units Sold, Revenue Share
    """
    expected_cols = ["Category", "Revenue", "Orders", "Units Sold", "Revenue Share"]
    if df.empty:
        return pd.DataFrame(columns=expected_cols)

    work_df = df.copy()
    
    # Resolve category labels defensively
    if "Category" in work_df.columns:
        work_df["Category"] = work_df["Category"].fillna("Unknown").astype(str).str.strip()
        work_df["Category"] = work_df["Category"].replace({'': 'Unknown', 'nan': 'Unknown'})
    else:
        work_df["Category"] = "Unknown"

    total_revenue = work_df["_Revenue"].sum()

    grouped = work_df.groupby("Category").agg(
        Revenue=("_Revenue", "sum"),
        Units_Sold=("Quantity", "sum"),
        Orders=("OrderID", "nunique")
    ).reset_index()

    if total_revenue > 0:
        grouped["Revenue Share"] = (grouped["Revenue"] / total_revenue) * 100.0
    else:
        grouped["Revenue Share"] = 0.0

    grouped = grouped.rename(columns={"Units_Sold": "Units Sold"})
    grouped = grouped.sort_values(by="Revenue", ascending=False).reset_index(drop=True)

    return grouped[expected_cols]


def calculate_city_performance(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """
    Computes performance broken down by City.
    If City column is absent (or has only missing values), returns None.
    Columns: City, Revenue, Orders, Units Sold, Revenue Share
    """
    if "City" not in df.columns or df["City"].isna().all():
        return None

    expected_cols = ["City", "Revenue", "Orders", "Units Sold", "Revenue Share"]
    if df.empty:
        return pd.DataFrame(columns=expected_cols)

    work_df = df.copy()
    work_df["City"] = work_df["City"].fillna("Unknown").astype(str).str.strip()
    work_df["City"] = work_df["City"].replace({'': 'Unknown', 'nan': 'Unknown'})

    total_revenue = work_df["_Revenue"].sum()

    grouped = work_df.groupby("City").agg(
        Revenue=("_Revenue", "sum"),
        Units_Sold=("Quantity", "sum"),
        Orders=("OrderID", "nunique")
    ).reset_index()

    if total_revenue > 0:
        grouped["Revenue Share"] = (grouped["Revenue"] / total_revenue) * 100.0
    else:
        grouped["Revenue Share"] = 0.0

    grouped = grouped.rename(columns={"Units_Sold": "Units Sold"})
    grouped = grouped.sort_values(by="Revenue", ascending=False).reset_index(drop=True)

    return grouped[expected_cols]


def calculate_payment_distribution(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """
    Calculates order-aware payment method distributions.
    Resolves multi-line items transactions conflict:
      - Groups rows by OrderID, taking the PaymentMethod specified on the first line item,
        aggregating gross/net revenues per OrderID first.
      - Calculates order counts, order share percentage, and revenue share.
    If column is missing, returns None.
    Columns: PaymentMethod, Orders, Revenue, Order Share (%)
    """
    if "PaymentMethod" not in df.columns or df["PaymentMethod"].isna().all():
        return None

    expected_cols = ["PaymentMethod", "Orders", "Revenue", "Order Share (%)"]
    if df.empty:
        return pd.DataFrame(columns=expected_cols)

    work_df = df.copy()
    
    # 1. Group by OrderID to get payment method (take first) and total order revenue
    order_summary = work_df.groupby("OrderID").agg(
        Order_Revenue=("_Revenue", "sum"),
        Order_Payment=("PaymentMethod", "first")
    ).reset_index()

    # 2. Clean values
    order_summary["Order_Payment"] = order_summary["Order_Payment"].fillna("Unknown").astype(str).str.strip()
    order_summary["Order_Payment"] = order_summary["Order_Payment"].replace({'': 'Unknown', 'nan': 'Unknown'})

    total_unique_orders = len(order_summary)

    # 3. Group by PaymentMethod
    grouped = order_summary.groupby("Order_Payment").agg(
        Revenue=("Order_Revenue", "sum"),
        Orders=("OrderID", "count")  # Each order has exactly 1 row in order_summary
    ).reset_index()

    if total_unique_orders > 0:
        grouped["Order Share (%)"] = (grouped["Orders"] / total_unique_orders) * 100.0
    else:
        grouped["Order Share (%)"] = 0.0

    grouped = grouped.rename(columns={"Order_Payment": "PaymentMethod"})
    grouped = grouped.sort_values(by="Orders", ascending=False).reset_index(drop=True)

    return grouped[expected_cols]


def detect_capabilities(df: pd.DataFrame) -> Dict[str, bool]:
    """
    Inspects columns in the raw/cleaned dataframe to flag analytics capabilities.
    """
    if df is None or df.empty:
        return {
            "core_kpis_available": False,
            "time_analytics_available": False,
            "category_analytics_available": False,
            "city_analytics_available": False,
            "payment_analytics_available": False,
            "profit_analytics_available": False
        }

    # Core required columns check
    required_kpis = ["OrderID", "OrderDate", "Quantity", "UnitPrice"]
    has_kpi_cols = all(col in df.columns for col in required_kpis)
    
    return {
        "core_kpis_available": has_kpi_cols,
        "time_analytics_available": "OrderDate" in df.columns and not df["OrderDate"].isna().all(),
        "category_analytics_available": "Category" in df.columns,
        "city_analytics_available": "City" in df.columns and not df["City"].isna().all(),
        "payment_analytics_available": "PaymentMethod" in df.columns and not df["PaymentMethod"].isna().all(),
        "profit_analytics_available": "UnitCost" in df.columns and not df["UnitCost"].isna().all()
    }


def apply_filters(
    df: pd.DataFrame, 
    date_range: Optional[Tuple[Any, Any]] = None,
    categories: Optional[List[str]] = None,
    cities: Optional[List[str]] = None,
    payment_methods: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Applies unified multi-select filters on a defensive copy of the prepared dataframe.
    """
    if df.empty:
        return df.copy()

    filtered_df = df.copy()

    # 1. Date filter
    if date_range and len(date_range) == 2:
        start_date, end_date = date_range
        if start_date is not None and end_date is not None:
            # Normalize to pandas timestamps
            ts_start = pd.to_datetime(start_date)
            ts_end = pd.to_datetime(end_date)
            filtered_df = filtered_df[
                (filtered_df["OrderDate"] >= ts_start) & 
                (filtered_df["OrderDate"] <= ts_end)
            ]

    # 2. Category filter
    if categories:
        # Fill missing dynamically during filtering to avoid losing them if "Unknown" filter is chosen
        cat_series = filtered_df["Category"].fillna("Unknown").astype(str).str.strip().replace({'': 'Unknown', 'nan': 'Unknown'})
        filtered_df = filtered_df[cat_series.isin(categories)]

    # 3. City filter
    if cities and "City" in filtered_df.columns:
        city_series = filtered_df["City"].fillna("Unknown").astype(str).str.strip().replace({'': 'Unknown', 'nan': 'Unknown'})
        filtered_df = filtered_df[city_series.isin(cities)]

    # 4. Payment method filter
    if payment_methods and "PaymentMethod" in filtered_df.columns:
        pm_series = filtered_df["PaymentMethod"].fillna("Unknown").astype(str).str.strip().replace({'': 'Unknown', 'nan': 'Unknown'})
        filtered_df = filtered_df[pm_series.isin(payment_methods)]

    return filtered_df
