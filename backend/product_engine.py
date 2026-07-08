import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, Optional, List
from backend.analytics_engine import prepare_analytics_dataset

def prepare_product_dataset(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Sub-prepares analytics-eligible dataset for product aggregation tracking.
    Integrates the shared prepared dataset calculations (exclusions, date formatting,
    revenue derivations) and enforces product identity validity.

    Product Identity rules:
      - Uses ProductID + ProductName if both exist.
      - Uses ProductID if only ProductID exists.
      - Uses ProductName if only ProductName exists.
      - If both columns exist but one is missing on a row, continues using the valid one.
      - Excludes a row only when no product identity can be resolved.
      
    Returns:
        (prepared_product_df, metadata)
    """
    # 1. Start with the shared analytics dataset preparation (covers OrderID, OrderDate, Quantity, UnitPrice, DiscountPct)
    prep_df, meta = prepare_analytics_dataset(df)
    
    # Track extra variables in metadata
    meta["product_exclusions"] = {
        "missing_product_identity": 0
    }
    meta["product_eligible_rows"] = 0
    
    if prep_df.empty:
        prep_df["Product_Key"] = pd.Series(dtype=str)
        prep_df["Product_Display"] = pd.Series(dtype=str)
        return prep_df, meta

    # Check columns
    has_id = "ProductID" in prep_df.columns
    has_name = "ProductName" in prep_df.columns

    product_keys = []
    product_displays = []
    valid_record_mask = []
    missing_identity_count = 0

    for _, row in prep_df.iterrows():
        pid_raw = row.get("ProductID", None)
        pname_raw = row.get("ProductName", None)

        # Parse string cleanly, checking for NaN/None
        pid = str(pid_raw).strip() if pd.notna(pid_raw) else ""
        pname = str(pname_raw).strip() if pd.notna(pname_raw) else ""

        # Normalize typical null-like strings
        if pid.lower() in ["nan", "none", "null", ""]:
            pid = ""
        if pname.lower() in ["nan", "none", "null", ""]:
            pname = ""

        # Exclusion if both are missing
        if has_id and has_name:
            if not pid and not pname:
                valid_record_mask.append(False)
                missing_identity_count += 1
            else:
                valid_record_mask.append(True)
                if pid and pname:
                    product_keys.append(f"{pid}|{pname}")
                    product_displays.append(f"[{pid}] {pname}")
                elif pid:
                    product_keys.append(pid)
                    product_displays.append(f"[{pid}]")
                else:
                    product_keys.append(pname)
                    product_displays.append(pname)
        elif has_id:
            if not pid:
                valid_record_mask.append(False)
                missing_identity_count += 1
            else:
                valid_record_mask.append(True)
                product_keys.append(pid)
                product_displays.append(pid)
        elif has_name:
            if not pname:
                valid_record_mask.append(False)
                missing_identity_count += 1
            else:
                valid_record_mask.append(True)
                product_keys.append(pname)
                product_displays.append(pname)
        else:
            # Neither identity column exists in schema
            valid_record_mask.append(False)
            missing_identity_count += 1

    # Keep only rows with valid product identity resolved
    product_df = prep_df[valid_record_mask].copy()
    
    if len(product_df) > 0:
        product_df["Product_Key"] = product_keys
        product_df["Product_Display"] = product_displays
    else:
        product_df["Product_Key"] = pd.Series(dtype=str)
        product_df["Product_Display"] = pd.Series(dtype=str)

    # Update metadata
    meta["product_eligible_rows"] = len(product_df)
    meta["product_exclusions"]["missing_product_identity"] = missing_identity_count
    # Add product specific counts to excluded total
    meta["excluded_row_count"] += missing_identity_count

    return product_df, meta

def apply_product_filters(
    df: pd.DataFrame,
    date_range: Optional[Tuple[Any, Any]] = None,
    categories: Optional[List[str]] = None,
    search_query: Optional[str] = None
) -> pd.DataFrame:
    """
    Applies filters on prepared product DataFrames (date range, categories, search text).
    """
    if df.empty:
        return df.copy()

    from backend.analytics_engine import apply_filters
    
    # 1. Apply date range and categories filters
    filtered_df = apply_filters(df, date_range=date_range, categories=categories)
    
    # 2. Apply text search query across product identifier values
    if search_query and len(search_query.strip()) > 0 and not filtered_df.empty:
        query = search_query.strip().lower()
        mask = pd.Series(False, index=filtered_df.index)
        
        if "ProductID" in filtered_df.columns:
            mask |= filtered_df["ProductID"].astype(str).str.lower().str.contains(query, na=False)
        if "ProductName" in filtered_df.columns:
            mask |= filtered_df["ProductName"].astype(str).str.lower().str.contains(query, na=False)
        if "Product_Display" in filtered_df.columns:
            mask |= filtered_df["Product_Display"].astype(str).str.lower().str.contains(query, na=False)
            
        filtered_df = filtered_df[mask]
        
    return filtered_df

def get_product_performance(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generates product performance summaries for active records.
    Filters must already be applied to df.
    
    Columns returned:
      - Product_Key
      - Product_Display
      - Revenue
      - Unique Orders (unique OrderID list)
      - Units Sold (sum of Quantity)
      - Average Realized Revenue per Unit (Revenue / Units Sold)
      - Average Price (mean of UnitPrice column)
      - Revenue Share (%)
      - Unit Share (%)
      - Revenue per Order (Revenue / Unique Orders)
      - Rank (by Revenue descending, ties broken alphabetically by display name)
    """
    expected_cols = [
        "Product_Key", "Product_Display", "Revenue", "Unique Orders", "Units Sold",
        "Average Realized Revenue per Unit", "Average Price", "Revenue Share (%)",
        "Unit Share (%)", "Revenue per Order", "Rank"
    ]
    
    if df.empty:
        return pd.DataFrame(columns=expected_cols)

    # 1. Group operations
    grouped = df.groupby(["Product_Key", "Product_Display"]).agg(
        Revenue=("_Revenue", "sum"),
        Units_Sold=("Quantity", "sum"),
        Unique_Orders=("OrderID", "nunique"),
        Avg_Price=("UnitPrice", "mean")
    ).reset_index()

    total_revenue = grouped["Revenue"].sum()
    total_units = grouped["Units_Sold"].sum()

    # 2. Derived metrics
    avg_realized = []
    rev_share = []
    unit_share = []
    rev_per_order = []

    for _, row in grouped.iterrows():
        rev = row["Revenue"]
        units = row["Units_Sold"]
        orders = row["Unique_Orders"]

        # Average Realized Revenue per Unit
        avg_realized.append(rev / units if units > 0 else 0.0)
        
        # Share values
        rev_share.append((rev / total_revenue * 100.0) if total_revenue > 0 else 0.0)
        unit_share.append((units / total_units * 100.0) if total_units > 0 else 0.0)
        
        # Revenue per Order
        rev_per_order.append(rev / orders if orders > 0 else 0.0)

    grouped["Average Realized Revenue per Unit"] = avg_realized
    grouped["Revenue Share (%)"] = rev_share
    grouped["Unit Share (%)"] = unit_share
    grouped["Revenue per Order"] = rev_per_order
    
    grouped = grouped.rename(columns={
        "Units_Sold": "Units Sold",
        "Unique_Orders": "Unique Orders",
        "Avg_Price": "Average Price"
    })

    # Sort descending by Revenue, then alphabetically by Product_Display to break ties
    grouped = grouped.sort_values(by=["Revenue", "Product_Display"], ascending=[False, True]).reset_index(drop=True)
    grouped["Rank"] = np.arange(1, len(grouped) + 1)

    return grouped[expected_cols]

def calculate_product_kpis(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes summary portfolio KPI cards details based on current filtered products.
    """
    defaults = {
        "total_active_products": 0,
        "top_product_by_revenue": "N/A",
        "top_product_by_units": "N/A",
        "avg_revenue_per_product": 0.0,
        "top_5_concentration_pct": 0.0
    }
    
    if df.empty:
        return defaults

    perf = get_product_performance(df)
    if perf.empty:
        return defaults

    total_active_products = len(perf)
    total_rev = perf["Revenue"].sum()
    
    # Top product by revenue (first row of sorted performance summary)
    top_rev_item = perf.iloc[0]["Product_Display"] if len(perf) > 0 else "N/A"
    
    # Top product by units sold (descending units sold, alphabetical name tie break)
    units_sorted = perf.sort_values(by=["Units Sold", "Product_Display"], ascending=[False, True]).reset_index(drop=True)
    top_unit_item = units_sorted.iloc[0]["Product_Display"] if len(units_sorted) > 0 else "N/A"

    # Avg revenue per product
    avg_rev = total_rev / total_active_products if total_active_products > 0 else 0.0

    # Top 5 concentration percentage
    top_5_rev = perf.head(5)["Revenue"].sum()
    top_5_concentration = (top_5_rev / total_rev * 100.0) if total_rev > 0 else 0.0

    return {
        "total_active_products": total_active_products,
        "top_product_by_revenue": top_rev_item,
        "top_product_by_units": top_unit_item,
        "avg_revenue_per_product": avg_rev,
        "top_5_concentration_pct": top_5_concentration
    }

def get_top_bottom_ranking(df: pd.DataFrame, n: int = 5) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Retrieves Top N and Bottom N products by Revenue.
    Ties broken deterministically by display name.
    """
    perf = get_product_performance(df)
    if perf.empty:
         return pd.DataFrame(), pd.DataFrame()

    # Top N products: Performance df is already sorted descending by Revenue
    top_n = perf.head(n).copy()

    # Bottom N products: Sort performance table ascending by Revenue, ties broken alphabetically
    bottom_sorted = perf.sort_values(by=["Revenue", "Product_Display"], ascending=[True, True]).reset_index(drop=True)
    bottom_n = bottom_sorted.head(n).copy()

    return top_n, bottom_n

def get_pareto_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Prepares Pareto cumulative contribution data.
    Orders products from highest to lowest revenue, computes cumulative shares,
    and isolates approximately ~80% revenue contributions.
    """
    default_meta = {
        "contributors_count": 0,
        "total_products": 0,
        "contributors_ratio_pct": 0.0,
        "contributor_displays": []
    }
    
    perf = get_product_performance(df)
    if perf.empty:
        return pd.DataFrame(columns=["Product_Display", "Revenue", "Revenue Share (%)", "Cumulative Pct"]), default_meta

    # Re-sort descending just in case
    pareto_df = perf[["Product_Display", "Revenue", "Revenue Share (%)"]].copy()
    pareto_df = pareto_df.sort_values(by=["Revenue", "Product_Display"], ascending=[False, True]).reset_index(drop=True)

    total_rev = pareto_df["Revenue"].sum()
    
    # Cumulative stats
    pareto_df["Cumulative Revenue"] = pareto_df["Revenue"].cumsum()
    
    if total_rev > 0:
        pareto_df["Cumulative Pct"] = (pareto_df["Cumulative Revenue"] / total_rev) * 100.0
    else:
        pareto_df["Cumulative Pct"] = 100.0

    # Locate products up to when cumulative percentage first reaches or exceeds 80%
    contributor_count = 0
    contributor_names = []
    
    if total_rev > 0:
        for idx, row in pareto_df.iterrows():
            contributor_count += 1
            contributor_names.append(row["Product_Display"])
            if row["Cumulative Revenue"] >= total_rev * 0.8:
                break

    meta_summary = {
        "contributors_count": contributor_count,
        "total_products": len(pareto_df),
        "contributors_ratio_pct": (contributor_count / len(pareto_df) * 100.0) if len(pareto_df) > 0 else 0.0,
        "contributor_displays": contributor_names
    }

    return pareto_df[["Product_Display", "Revenue", "Revenue Share (%)", "Cumulative Pct"]], meta_summary

def get_quadrant_analysis_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, float]]:
    """
    Computes relative volume-value metrics for Products Scatter Analysis.
    Classifications are relative to the currently filtered portfolio's median thresholds.
    
    Equality rules:
       - Units Sold >= median_units -> high-volume
       - Revenue >= median_revenue -> high-revenue
    """
    perf = get_product_performance(df)
    
    if perf.empty:
         return pd.DataFrame(columns=["Product_Display", "Units Sold", "Revenue", "Average Realized Revenue per Unit", "Quadrant"]), {"median_units": 0.0, "median_revenue": 0.0}

    med_units = float(perf["Units Sold"].median())
    med_revenue = float(perf["Revenue"].median())

    quadrants = []
    for _, row in perf.iterrows():
        units = row["Units Sold"]
        rev = row["Revenue"]

        if units >= med_units and rev >= med_revenue:
            quadrants.append("high-volume / high-revenue")
        elif units >= med_units and rev < med_revenue:
            quadrants.append("high-volume / low-revenue")
        elif units < med_units and rev >= med_revenue:
            quadrants.append("low-volume / high-revenue")
        else:
            quadrants.append("low-volume / low-revenue")

    perf_quad = perf[["Product_Display", "Units Sold", "Revenue", "Average Realized Revenue per Unit"]].copy()
    perf_quad["Quadrant"] = quadrants

    thresholds = {
        "median_units": med_units,
        "median_revenue": med_revenue
    }

    return perf_quad, thresholds

def get_category_product_context(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """
    Groups product performance details at a Category level context.
    If Category column is absent, returns None.
    """
    if "Category" not in df.columns:
        return None

    expected_cols = ["Category", "Active Products", "Revenue", "Units Sold", "Top Product"]
    if df.empty:
        return pd.DataFrame(columns=expected_cols)

    # Copy to avoid side-effects
    work_df = df.copy()
    
    # Standardize category labels
    work_df["Category"] = work_df["Category"].fillna("Unknown").astype(str).str.strip().replace({'': 'Unknown', 'nan': 'Unknown'})
    
    # 1. Group overall metrics
    grouped_stats = work_df.groupby("Category").agg(
        Revenue=("_Revenue", "sum"),
        Units_Sold=("Quantity", "sum")
    ).reset_index()

    # 2. Get unique products count per Category
    # We must resolve product identity exactly first
    # Work on prepared df
    prod_df, _ = prepare_product_dataset(df)
    if prod_df.empty:
        grouped_stats["Active Products"] = 0
        grouped_stats["Top Product"] = "N/A"
        return grouped_stats.rename(columns={"Units_Sold": "Units Sold"})[expected_cols]

    # Category active product count
    prod_counts = prod_df.groupby("Category")["Product_Key"].nunique().reset_index().rename(columns={"Product_Key": "Active Products"})
    
    # Top product per Category
    top_prods_list = []
    # Identify product sales per Category
    prod_sales = prod_df.groupby(["Category", "Product_Display"]).agg(Revenue=("_Revenue", "sum")).reset_index()
    
    for cat in grouped_stats["Category"]:
        cat_subset = prod_sales[prod_sales["Category"] == cat]
        if cat_subset.empty:
            top_prods_list.append("N/A")
        else:
            # Deterministic sorting (descending revenue, alphabetical display name)
            cat_sorted = cat_subset.sort_values(by=["Revenue", "Product_Display"], ascending=[False, True])
            top_prods_list.append(cat_sorted.iloc[0]["Product_Display"])

    # Merge
    merged = pd.merge(grouped_stats, prod_counts, on="Category", how="left").fillna(0)
    merged["Active Products"] = merged["Active Products"].astype(int)
    merged["Top Product"] = top_prods_list
    
    merged = merged.rename(columns={"Units_Sold": "Units Sold"})
    merged = merged.sort_values(by="Revenue", ascending=False).reset_index(drop=True)

    return merged[expected_cols]

def detect_product_capabilities(df: pd.DataFrame) -> Dict[str, bool]:
    """
    Audits column lists representing whether products intelligence dashboards can render.
    """
    if df is None or df.empty:
        return {
            "product_identity_available": False,
            "category_available": False,
            "quantity_analysis_available": False,
            "revenue_analysis_available": False,
            "pricing_analysis_available": False
        }

    has_id = "ProductID" in df.columns
    has_name = "ProductName" in df.columns
    has_qty = "Quantity" in df.columns
    has_price = "UnitPrice" in df.columns

    return {
        "product_identity_available": has_id or has_name,
        "category_available": "Category" in df.columns,
        "quantity_analysis_available": has_qty,
        "revenue_analysis_available": has_qty and has_price,
        "pricing_analysis_available": has_qty and has_price
    }
