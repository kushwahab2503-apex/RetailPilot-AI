import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, Optional, List
from backend.analytics_engine import prepare_analytics_dataset

def prepare_customer_dataset(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Sub-prepares analytics-eligible dataset for customer performance tracking.
    Integrates the shared prepared dataset calculations (exclusions, date formatting,
    revenue derivations) and enforces customer identity rules.

    Customer Identity rules:
      - Uses CustomerID + CustomerName if both exist.
      - Uses CustomerID if only CustomerID exists.
      - Uses CustomerName if only CustomerName exists.
      - If both columns exist but one is missing on a row, continues using the valid one.
      - Excludes a row only when no customer identity can be resolved.
      
    Returns:
        (prepared_customer_df, metadata)
    """
    # 1. Start with the shared analytics dataset preparation (covers OrderID, OrderDate, Quantity, UnitPrice, DiscountPct)
    prep_df, meta = prepare_analytics_dataset(df)
    
    meta["customer_exclusions"] = {
        "missing_customer_identity": 0
    }
    meta["customer_eligible_rows"] = 0
    
    meta["working_row_count"] = meta.get("row_count_analyzed", 0)
    meta["eligible_row_count"] = meta.get("valid_row_count", 0)
    
    if prep_df.empty:
        prep_df["Customer_Key"] = pd.Series(dtype=str)
        prep_df["Customer_Display"] = pd.Series(dtype=str)
        return prep_df, meta

    # Check columns
    has_id = "CustomerID" in prep_df.columns
    has_name = "CustomerName" in prep_df.columns

    customer_keys = []
    customer_displays = []
    valid_record_mask = []
    missing_identity_count = 0

    for _, row in prep_df.iterrows():
        cid_raw = row.get("CustomerID", None)
        cname_raw = row.get("CustomerName", None)

        cid = str(cid_raw).strip() if pd.notna(cid_raw) else ""
        cname = str(cname_raw).strip() if pd.notna(cname_raw) else ""

        # Normalize typical null-like strings
        if cid.lower() in ["nan", "none", "null", ""]:
            cid = ""
        if cname.lower() in ["nan", "none", "null", ""]:
            cname = ""

        # Identity Checks
        if Cid_valid := (cid != ""):
            pass
        if Cname_valid := (cname != ""):
            pass

        if has_id and has_name:
            if not Cid_valid and not Cname_valid:
                valid_record_mask.append(False)
                missing_identity_count += 1
            else:
                valid_record_mask.append(True)
                if Cid_valid and Cname_valid:
                    customer_keys.append(f"{cid}|{cname}")
                    customer_displays.append(f"[{cid}] {cname}")
                elif Cid_valid:
                    customer_keys.append(cid)
                    customer_displays.append(f"[{cid}]")
                else:
                    customer_keys.append(cname)
                    customer_displays.append(cname)
        elif has_id:
            if not Cid_valid:
                valid_record_mask.append(False)
                missing_identity_count += 1
            else:
                valid_record_mask.append(True)
                customer_keys.append(cid)
                customer_displays.append(cid)
        elif has_name:
            if not Cname_valid:
                valid_record_mask.append(False)
                missing_identity_count += 1
            else:
                valid_record_mask.append(True)
                customer_keys.append(cname)
                customer_displays.append(cname)
        else:
            # Neither identity column exists in schema
            valid_record_mask.append(False)
            missing_identity_count += 1

    customer_df = prep_df[valid_record_mask].copy()
    
    if len(customer_df) > 0:
        customer_df["Customer_Key"] = customer_keys
        customer_df["Customer_Display"] = customer_displays
    else:
        customer_df["Customer_Key"] = pd.Series(dtype=str)
        customer_df["Customer_Display"] = pd.Series(dtype=str)

    # Update metadata
    meta["customer_eligible_rows"] = len(customer_df)
    meta["customer_exclusions"]["missing_customer_identity"] = missing_identity_count
    # Add customer specific counts to excluded total
    meta["excluded_row_count"] += missing_identity_count
    
    meta["working_row_count"] = meta["row_count_analyzed"]
    meta["eligible_row_count"] = meta["valid_row_count"] - missing_identity_count

    return customer_df, meta

def assign_tie_aware_scores(values: pd.Series, ascending: bool = True) -> pd.Series:
    """
    Assigns RFM scores (1 to 5) deterministically based on rank percentiles,
    ensuring that identical metric values always receive identical scores.
    
    Strategy:
      - Unique values are sorted.
      - Each unique value is assigned a score in the range [1, 5] based on its position index.
      - This score is mapped back to the original series.
      - Collapsed/constant values or single-item datasets get Score 5.
    """
    if values.empty:
        return pd.Series(dtype=int)
        
    unique_vals = sorted(values.dropna().unique())
    if len(unique_vals) <= 1:
        return pd.Series(5, index=values.index)
        
    val_to_score = {}
    n = len(unique_vals)
    for idx, val in enumerate(unique_vals):
        pct = idx / (n - 1)
        if not ascending:
            pct = 1.0 - pct
        # Map [0, 1] scale to [1, 5]
        score = int(round(1 + pct * 4))
        val_to_score[val] = score
        
    mapped_series = values.map(val_to_score)
    # Fill remaining values defensively and type coerce
    return mapped_series.fillna(3).astype(int)

def calculate_lifetime_customer_base(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes a customer-level historical database on the full prepared source dataset.
    This establishes baseline classifications stable across dynamic date filters.
    
    Fields calculated:
      - Customer_Key
      - Customer_Display
      - Lifetime_First_Purchase_Date
      - Lifetime_Last_Purchase_Date
      - Lifetime_Unique_Orders (Frequency)
      - Lifetime_Repeat_Status ("Repeat Customer" if orders > 1, else "One-Time Customer")
      - Lifetime_Revenue (Monetary)
      - Days_Since_Last_Purchase_Lifetime (Recency)
      - R_Score, F_Score, M_Score
      - Lifetime_Segment
    """
    if df.empty:
        cols = [
            "Customer_Key", "Customer_Display", "Lifetime_First_Purchase_Date",
            "Lifetime_Last_Purchase_Date", "Lifetime_Unique_Orders", "Lifetime_Repeat_Status",
            "Lifetime_Revenue", "Days_Since_Last_Purchase_Lifetime", "R_Score", "F_Score", "M_Score",
            "Lifetime_Segment"
        ]
        return pd.DataFrame(columns=cols)

    # 1. Base aggregations
    grouped = df.groupby(["Customer_Key", "Customer_Display"]).agg(
        Lifetime_First_Purchase_Date=("OrderDate", "min"),
        Lifetime_Last_Purchase_Date=("OrderDate", "max"),
        Lifetime_Unique_Orders=("OrderID", "nunique"),
        Lifetime_Revenue=("_Revenue", "sum")
    ).reset_index()

    # Recency reference date (maximum date in the active full database)
    max_date = df["OrderDate"].max()
    
    # Calculate Recency in days
    grouped["Days_Since_Last_Purchase_Lifetime"] = (max_date - grouped["Lifetime_Last_Purchase_Date"]).dt.days

    # 2. RFM Scores
    # Recency: Smaller days is better -> ascending=False
    grouped["R_Score"] = assign_tie_aware_scores(grouped["Days_Since_Last_Purchase_Lifetime"], ascending=False)
    # Frequency: Larger order count is better -> ascending=True
    grouped["F_Score"] = assign_tie_aware_scores(grouped["Lifetime_Unique_Orders"], ascending=True)
    # Monetary: Larger revenue is better -> ascending=True
    grouped["M_Score"] = assign_tie_aware_scores(grouped["Lifetime_Revenue"], ascending=True)

    # 3. Repeat status
    status = []
    for orders in grouped["Lifetime_Unique_Orders"]:
        status.append("Repeat Customer" if orders > 1 else "One-Time Customer")
    grouped["Lifetime_Repeat_Status"] = status

    # 4. Segment Mapping Rules
    segments = []
    for _, row in grouped.iterrows():
        r = row["R_Score"]
        f = row["F_Score"]
        m = row["M_Score"]

        if r >= 4 and f >= 4 and m >= 4:
            segments.append("Champions")
        elif r >= 3 and f >= 3:
            segments.append("Loyal Customers")
        elif r >= 3 and m >= 2:
            segments.append("Potential Loyalists")
        elif r >= 4 and f == 1:
            segments.append("New Customers")
        elif r <= 2 and f >= 2:
            segments.append("At Risk")
        else:
            segments.append("Hibernating")

    grouped["Lifetime_Segment"] = segments

    return grouped

def get_customer_period_performance(
    filtered_period_df: pd.DataFrame,
    lifetime_base_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Combines the lifetime customer base and aggregates period-sensitive statistics.
    Sorted by Filtered Revenue descending. Deterministic tie-breaker is Customer_Display ascending.
    """
    expected_cols = [
        "Customer_Key", "Customer_Display", "Filtered_Revenue", "Filtered_Orders",
        "Filtered_Units_Purchased", "Filtered_AOV", "Revenue_Share_Pct", "Order_Share_Pct",
        "Lifetime_Segment", "Lifetime_Repeat_Status", "Customer_Revenue_Rank"
    ]
    
    if lifetime_base_df.empty:
        return pd.DataFrame(columns=expected_cols)

    if filtered_period_df.empty:
        # Create default empty records representation
        res = lifetime_base_df[["Customer_Key", "Customer_Display", "Lifetime_Segment", "Lifetime_Repeat_Status"]].copy()
        res["Filtered_Revenue"] = 0.0
        res["Filtered_Orders"] = 0
        res["Filtered_Units_Purchased"] = 0
        res["Filtered_AOV"] = 0.0
        res["Revenue_Share_Pct"] = 0.0
        res["Order_Share_Pct"] = 0.0
        res["Customer_Revenue_Rank"] = np.arange(1, len(res) + 1)
        return res[expected_cols]

    # Aggregate filtered period stats
    period_grouped = filtered_period_df.groupby("Customer_Key").agg(
        Filtered_Revenue=("_Revenue", "sum"),
        Filtered_Units_Purchased=("Quantity", "sum"),
        Filtered_Orders=("OrderID", "nunique")
    ).reset_index()

    total_filtered_revenue = period_grouped["Filtered_Revenue"].sum()
    total_filtered_orders = period_grouped["Filtered_Orders"].sum()

    # Merge period statistics onto full lifetime metadata
    merged = pd.merge(
        lifetime_base_df[["Customer_Key", "Customer_Display", "Lifetime_Segment", "Lifetime_Repeat_Status"]],
        period_grouped,
        on="Customer_Key",
        how="left"
    ).fillna(0.0)

    # Type coercion
    merged["Filtered_Orders"] = merged["Filtered_Orders"].astype(int)
    merged["Filtered_Units_Purchased"] = merged["Filtered_Units_Purchased"].astype(int)

    # Share and AOV Calculations
    aov_list = []
    rev_share = []
    ord_share = []
    
    for _, row in merged.iterrows():
        rev = row["Filtered_Revenue"]
        ords = row["Filtered_Orders"]

        aov_list.append(rev / ords if ords > 0 else 0.0)
        rev_share.append((rev / total_filtered_revenue * 100.0) if total_filtered_revenue > 0 else 0.0)
        ord_share.append((ords / total_filtered_orders * 100.0) if total_filtered_orders > 0 else 0.0)

    merged["Filtered_AOV"] = aov_list
    merged["Revenue_Share_Pct"] = rev_share
    merged["Order_Share_Pct"] = ord_share

    # Sort deterministically
    merged = merged.sort_values(by=["Filtered_Revenue", "Customer_Display"], ascending=[False, True]).reset_index(drop=True)
    merged["Customer_Revenue_Rank"] = np.arange(1, len(merged) + 1)

    return merged[expected_cols]

def calculate_customer_kpis(
    filtered_period_df: pd.DataFrame,
    lifetime_base_df: pd.DataFrame
) -> Dict[str, Any]:
    """
    Computes overall summary KPIs.
    """
    defaults = {
        "active_customers_period": 0,
        "total_revenue_period": 0.0,
        "repeat_customer_rate_lifetime": 0.0,
        "onetime_customer_rate_lifetime": 0.0,
        "avg_revenue_per_customer_period": 0.0,
        "avg_orders_per_customer_period": 0.0,
        "top_customer_by_revenue_period": "N/A",
        "top_customer_by_orders_period": "N/A",
        "top_5_concentration_pct_period": 0.0
    }

    if lifetime_base_df.empty:
        return defaults

    # Lifetime metrics
    tot_customers = len(lifetime_base_df)
    n_repeat = len(lifetime_base_df[lifetime_base_df["Lifetime_Repeat_Status"] == "Repeat Customer"])
    
    repeat_rate_lifetime = (n_repeat / tot_customers * 100.0) if tot_customers > 0 else 0.0
    onetime_rate_lifetime = ( (tot_customers - n_repeat) / tot_customers * 100.0) if tot_customers > 0 else 0.0

    if filtered_period_df.empty:
        res = defaults.copy()
        res["repeat_customer_rate_lifetime"] = repeat_rate_lifetime
        res["onetime_customer_rate_lifetime"] = onetime_rate_lifetime
        return res

    # Period statistics
    active_customers_period = filtered_period_df["Customer_Key"].nunique()
    total_rev = filtered_period_df["_Revenue"].sum()
    total_orders = filtered_period_df["OrderID"].nunique()

    avg_rev = total_rev / active_customers_period if active_customers_period > 0 else 0.0
    avg_orders = total_orders / active_customers_period if active_customers_period > 0 else 0.0

    # Get ranking summaries
    perf = get_customer_period_performance(filtered_period_df, lifetime_base_df)
    
    # Top Customer by Revenue (first row is top)
    top_rev_cust = perf.iloc[0]["Customer_Display"] if len(perf) > 0 and perf.iloc[0]["Filtered_Revenue"] > 0 else "N/A"
    
    # Top Customer by Order Count
    orders_sorted = perf.sort_values(by=["Filtered_Orders", "Customer_Display"], ascending=[False, True]).reset_index(drop=True)
    top_ord_cust = orders_sorted.iloc[0]["Customer_Display"] if len(orders_sorted) > 0 and orders_sorted.iloc[0]["Filtered_Orders"] > 0 else "N/A"

    # Top 5 Revenue Concentration
    top_5_rev = perf.head(5)["Filtered_Revenue"].sum()
    concentration = (top_5_rev / total_rev * 100.0) if total_rev > 0 else 0.0

    return {
        "active_customers_period": active_customers_period,
        "total_revenue_period": total_rev,
        "repeat_customer_rate_lifetime": repeat_rate_lifetime,
        "onetime_customer_rate_lifetime": onetime_rate_lifetime,
        "avg_revenue_per_customer_period": avg_rev,
        "avg_orders_per_customer_period": avg_orders,
        "top_customer_by_revenue_period": top_rev_cust,
        "top_customer_by_orders_period": top_ord_cust,
        "top_5_concentration_pct_period": concentration
    }

def get_repeat_vs_onetime_summary(
    filtered_period_df: pd.DataFrame,
    lifetime_base_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Aggregates filtered-period performance grouped strictly by baseline Lifetime repeat status.
    """
    expected_cols = ["Repeat Status", "Customer Count", "Revenue", "Revenue Share (%)", "Orders", "Average Order Value", "Units Purchased"]
    if lifetime_base_df.empty:
        return pd.DataFrame(columns=expected_cols)

    # Resolve performance listing
    perf = get_customer_period_performance(filtered_period_df, lifetime_base_df)
    
    # Group by baseline status
    grouped = perf.groupby("Lifetime_Repeat_Status").agg(
        Customer_Count=("Customer_Key", "nunique"), # Note: counts all available in category
        Revenue=("Filtered_Revenue", "sum"),
        Orders=("Filtered_Orders", "sum"),
        Units=("Filtered_Units_Purchased", "sum")
    ).reset_index()

    total_revenue = grouped["Revenue"].sum()

    res_list = []
    for _, row in grouped.iterrows():
        status = row["Lifetime_Repeat_Status"]
        cnt = row["Customer_Count"]
        rev = row["Revenue"]
        ords = row["Orders"]
        units = row["Units"]

        rev_share = (rev / total_revenue * 100.0) if total_revenue > 0 else 0.0
        aov = (rev / ords) if ords > 0 else 0.0

        res_list.append({
            "Repeat Status": status,
            "Customer Count": cnt,
            "Revenue": rev,
            "Revenue Share (%)": rev_share,
            "Orders": ords,
            "Average Order Value": aov,
            "Units Purchased": units
        })

    # Ensure both classifications exist in output table for comparative integrity
    out_df = pd.DataFrame(res_list)
    for st in ["Repeat Customer", "One-Time Customer"]:
        if out_df.empty or st not in out_df["Repeat Status"].values:
            extra = pd.DataFrame([{
                "Repeat Status": st,
                "Customer Count": len(lifetime_base_df[lifetime_base_df["Lifetime_Repeat_Status"] == st]),
                "Revenue": 0.0,
                "Revenue Share (%)": 0.0,
                "Orders": 0,
                "Average Order Value": 0.0,
                "Units Purchased": 0
            }])
            out_df = pd.concat([out_df, extra], ignore_index=True)

    return out_df

def get_customer_ranking_views(
    filtered_period_df: pd.DataFrame,
    lifetime_base_df: pd.DataFrame,
    n: int = 5
) -> Dict[str, pd.DataFrame]:
    """
    Returns top customer Leaderboards for:
      - Revenue
      - Order Count
      - Units Purchased
      
    Ties resolved deterministically by Customer_Display ascending.
    """
    perf = get_customer_period_performance(filtered_period_df, lifetime_base_df)
    
    # Hide rankings if no transactions exist in the period
    active_perf = perf[perf["Filtered_Revenue"] > 0].copy()

    if active_perf.empty:
        empty_lbl = ["Customer_Display"] + ["Metric Value"]
        return {
            "Top_Revenue": pd.DataFrame(columns=["Rank", "Customer_Display", "Revenue"]),
            "Top_Orders": pd.DataFrame(columns=["Rank", "Customer_Display", "Orders"]),
            "Top_Units": pd.DataFrame(columns=["Rank", "Customer_Display", "Units"])
        }

    # 1. Top Revenue
    rev_sorted = active_perf.sort_values(by=["Filtered_Revenue", "Customer_Display"], ascending=[False, True]).head(n).reset_index(drop=True)
    rev_sorted["Rank"] = np.arange(1, len(rev_sorted) + 1)

    # 2. Top Orders
    ord_sorted = active_perf.sort_values(by=["Filtered_Orders", "Customer_Display"], ascending=[False, True]).head(n).reset_index(drop=True)
    ord_sorted["Rank"] = np.arange(1, len(ord_sorted) + 1)

    # 3. Top Units
    unit_sorted = active_perf.sort_values(by=["Filtered_Units_Purchased", "Customer_Display"], ascending=[False, True]).head(n).reset_index(drop=True)
    unit_sorted["Rank"] = np.arange(1, len(unit_sorted) + 1)

    return {
        "Top_Revenue": rev_sorted[["Rank", "Customer_Display", "Filtered_Revenue"]].rename(columns={"Filtered_Revenue": "Revenue"}),
        "Top_Orders": ord_sorted[["Rank", "Customer_Display", "Filtered_Orders"]].rename(columns={"Filtered_Orders": "Orders"}),
        "Top_Units": unit_sorted[["Rank", "Customer_Display", "Filtered_Units_Purchased"]].rename(columns={"Filtered_Units_Purchased": "Units"})
    }

def get_customer_concentration_data(
    filtered_period_df: pd.DataFrame,
    lifetime_base_df: pd.DataFrame
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Assesses customer concentration percentages and Pareto distribution analysis.
    """
    default_meta = {
        "contributors_count": 0,
        "total_active_customers": 0,
        "contributors_ratio_pct": 0.0,
        "contributor_displays": []
    }

    if lifetime_base_df.empty or filtered_period_df.empty:
        return pd.DataFrame(columns=["Customer_Display", "Revenue", "Revenue Share (%)", "Cumulative Pct"]), default_meta

    perf = get_customer_period_performance(filtered_period_df, lifetime_base_df)
    active_perf = perf[perf["Filtered_Revenue"] > 0].copy()
    active_perf = active_perf.sort_values(by=["Filtered_Revenue", "Customer_Display"], ascending=[False, True]).reset_index(drop=True)

    total_rev = active_perf["Filtered_Revenue"].sum()
    active_perf["Cumulative_Revenue"] = active_perf["Filtered_Revenue"].cumsum()

    if total_rev > 0:
        active_perf["Cumulative_Pct"] = (active_perf["Cumulative_Revenue"] / total_rev) * 100.0
    else:
        active_perf["Cumulative_Pct"] = 100.0

    contributor_count = 0
    contributor_names = []

    if total_rev > 0:
        for idx, row in active_perf.iterrows():
            contributor_count += 1
            contributor_names.append(row["Customer_Display"])
            if row["Cumulative_Revenue"] >= total_rev * 0.8:
                break

    meta = {
        "contributors_count": contributor_count,
        "total_active_customers": len(active_perf),
        "contributors_ratio_pct": (contributor_count / len(active_perf) * 100.0) if len(active_perf) > 0 else 0.0,
        "contributor_displays": contributor_names
    }

    out_df = active_perf[["Customer_Display", "Filtered_Revenue", "Revenue_Share_Pct", "Cumulative_Pct"]].rename(columns={
        "Filtered_Revenue": "Revenue",
        "Revenue_Share_Pct": "Revenue Share (%)",
        "Cumulative_Pct": "Cumulative Pct"
    })

    return out_df, meta

def get_geographic_customer_performance(
    filtered_period_df: pd.DataFrame,
    lifetime_base_df: pd.DataFrame
) -> Optional[pd.DataFrame]:
    """
    Groups customer stats at City geographic level.
    If City column is absent, returns None.
    """
    if "City" not in filtered_period_df.columns:
        return None

    expected_cols = ["City", "Active Customers", "Revenue", "Orders", "Avg Revenue per Customer", "Repeat Customer Rate (%)"]

    if filtered_period_df.empty:
        return pd.DataFrame(columns=expected_cols)

    # Copy to prevent side effects
    work_df = filtered_period_df.copy()
    work_df["City"] = work_df["City"].fillna("Unknown").astype(str).str.strip().replace({'': 'Unknown', 'nan': 'Unknown'})

    # 1. Geographic baseline groupings
    grouped = work_df.groupby("City").agg(
        Active_Customers=("Customer_Key", "nunique"),
        Revenue=("_Revenue", "sum"),
        Orders=("OrderID", "nunique")
    ).reset_index()

    # 2. Compute repeat customer rate within respective cities (based on lifetime status)
    repeat_rates = []
    for city in grouped["City"]:
        # Find all customer keys active in this city in filtered period
        cust_keys = work_df[work_df["City"] == city]["Customer_Key"].unique()
        # Look up baseline lifetime status of these customer keys
        subset_base = lifetime_base_df[lifetime_base_df["Customer_Key"].isin(cust_keys)]
        
        tot_c = len(subset_base)
        rep_c = len(subset_base[subset_base["Lifetime_Repeat_Status"] == "Repeat Customer"])
        rate = (rep_c / tot_c * 100.0) if tot_c > 0 else 0.0
        repeat_rates.append(rate)

    grouped["Repeat Customer Rate (%)"] = repeat_rates
    grouped["Avg Revenue per Customer"] = grouped["Revenue"] / grouped["Active_Customers"]

    grouped = grouped.rename(columns={
        "Active_Customers": "Active Customers",
        "Orders": "Orders"
    })
    grouped = grouped.sort_values(by="Revenue", ascending=False).reset_index(drop=True)

    return grouped[expected_cols]

def get_cohort_matrix_data(
    df: pd.DataFrame
) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """
    Build MoM Customer Cohort sizes and loyalty retention ratios matrix.
    Uses month of acquisition (first purchase date on full history) as cohort index.
    
    Returns:
      (cohort_counts, cohort_retention) or (None, None)
    """
    # Defensive checks on counts & months length
    caps = detect_customer_capabilities(df)
    if not caps["cohort_analysis_available"]:
        return None, None

    # Resolve customer keys
    customer_df = df.copy()
    
    # 1. Calculate acquisition month for each customer
    acq_db = customer_df.groupby("Customer_Key")["OrderDate"].min().dt.to_period("M").reset_index()
    acq_db = acq_db.rename(columns={"OrderDate": "Acquisition_Cohort"})

    # Merge acquisition cohort back to transactions
    merged = pd.merge(customer_df, acq_db, on="Customer_Key", how="left")
    merged["Transaction_Month"] = merged["OrderDate"].dt.to_period("M")

    # 2. Pivot to count active customers per cohort month offset
    # offset in months
    grouped = merged.groupby(["Acquisition_Cohort", "Transaction_Month"])["Customer_Key"].nunique().reset_index()
    
    # Calculate month index offset: e.g. Cohort '2026-07', Transaction_Month '2026-08' -> Offset index = 1
    # Period objects allow simple subtraction
    grouped["Cohort_Period_Offset"] = (grouped["Transaction_Month"] - grouped["Acquisition_Cohort"]).apply(lambda x: x.n)

    # Pivot table
    cohort_pivot = grouped.pivot(index="Acquisition_Cohort", columns="Cohort_Period_Offset", values="Customer_Key")
    
    # Size denotes active count in period 0
    cohort_sizes = cohort_pivot[0].copy()

    # Retention rate (divide by size)
    cohort_retention = cohort_pivot.divide(cohort_sizes, axis=0) * 100.0

    # Ensure indexes are string formatted cleanly for Streamlit charts
    cohort_pivot.index = cohort_pivot.index.astype(str)
    cohort_retention.index = cohort_retention.index.astype(str)

    # Format cohort counts for return
    counts_df = pd.DataFrame(cohort_pivot)
    retention_df = pd.DataFrame(cohort_retention)

    return counts_df, retention_df

def detect_customer_capabilities(df: pd.DataFrame) -> Dict[str, bool]:
    """
    Audits column lists representing customer intelligence options availability.
    Includes strict data conditions checks for cohort matrices models.
    """
    if df is None or df.empty:
        return {
            "customer_identity_available": False,
            "customer_name_available": False,
            "city_available": False,
            "transaction_history_available": False,
            "segmentation_available": False,
            "repeat_analysis_available": False,
            "cohort_analysis_available": False
        }

    has_id = "CustomerID" in df.columns
    has_name = "CustomerName" in df.columns
    has_city = "City" in df.columns
    has_date = "OrderDate" in df.columns

    # Basic identity
    cid_av = has_id or has_name

    # Cohort Analysis conditions checking:
    cohort_av = False
    if cid_av and has_date and len(df) > 0:
        # Standardize dates defensively
        dates = pd.to_datetime(df["OrderDate"], errors="coerce").dropna()
        if not dates.empty:
            date_span = (dates.max() - dates.min()).days
            unique_months = dates.dt.to_period("M").nunique()
            
            # Prepare customer keys check
            cust_keys = []
            if has_id:
                cust_keys = df["CustomerID"].dropna().unique()
            else:
                cust_keys = df["CustomerName"].dropna().unique()
            
            n_customers = len(cust_keys)
            
            # Check cohorts: compute cohort sizes
            # Acquire first purchase dates MoM
            if n_customers >= 5 and unique_months >= 3 and date_span >= 60:
                cohort_av = True

    return {
        "customer_identity_available": cid_av,
        "customer_name_available": has_name,
        "city_available": has_city,
        "transaction_history_available": len(df) > 0,
        "segmentation_available": cid_av and len(df) > 0,
        "repeat_analysis_available": cid_av and len(df) > 0,
        "cohort_analysis_available": cohort_av
    }
