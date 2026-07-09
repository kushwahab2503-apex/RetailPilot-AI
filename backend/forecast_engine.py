import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any, List, Optional
from datetime import datetime

from backend.analytics_engine import prepare_analytics_dataset, aggregate_time_series

def prepare_forecast_dataset(df: pd.DataFrame, category: Optional[str] = None) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Sub-prepares analytics-eligible dataset for forecasting.
    Normalizes columns, applies analytics exclusions, and optionally filters by Category.
    """
    prepared_df, meta = prepare_analytics_dataset(df)
    
    canonical_meta = {
        "working_row_count": meta.get("row_count_analyzed", 0),
        "eligible_row_count": meta.get("valid_row_count", 0),
        "aggregated_period_count": 0,
        "non_zero_period_count": 0,
        "date_span_days": 0,
        "coverage_ratio": 0.0,
        "selected_frequency": "Daily",
        "capability_state": "UNAVAILABLE",
        "capability_reasons": ["Dataset uninitialized"],
        "validation_status": "None (Insufficient History)"
    }
    
    if prepared_df.empty:
        return prepared_df, canonical_meta

    if category and "Category" in prepared_df.columns:
        filtered_df = prepared_df[prepared_df["Category"].fillna("Unknown").astype(str).str.strip().replace({'': 'Unknown', 'nan': 'Unknown'}) == category].copy()
    else:
        filtered_df = prepared_df.copy()

    return filtered_df, canonical_meta


def detect_forecast_capabilities(df: pd.DataFrame, selected_frequency: str) -> Dict[str, Any]:
    """
    Determines if the dataset is suitable for forecasting at the selected frequency
    using mutually exclusive capability states.
    
    A. UNAVAILABLE:
    If any hard minimum fails:
    - date_span_days < 14
    - aggregated_period_count < M
    - non_zero_period_count < 3
    - coverage_ratio < 0.20

    B. SUITABLE:
    If all strong conditions pass:
    - date_span_days >= 45
    - aggregated_period_count >= M + H
    - non_zero_period_count >= 5
    - coverage_ratio >= 0.50

    C. LIMITED:
    Every dataset that passes UNAVAILABLE hard minimums but does not satisfy all SUITABLE conditions.
    """
    # Define validation and minimum parameters per frequency
    if selected_frequency == "Monthly":
        M, H = 6, 3
    elif selected_frequency == "Weekly":
        M, H = 8, 4
    else:  # Daily
        M, H = 14, 7

    reasons = []
    
    # 0. Basic validation checks
    if df is None or df.empty or "OrderDate" not in df.columns:
        return {
            "working_row_count": 0,
            "eligible_row_count": 0,
            "aggregated_period_count": 0,
            "non_zero_period_count": 0,
            "date_span_days": 0,
            "coverage_ratio": 0.0,
            "selected_frequency": selected_frequency,
            "capability_state": "UNAVAILABLE",
            "capability_reasons": ["Dataset is empty or has no valid date columns"],
            "validation_status": "None (Insufficient History)"
        }

    # Find span of time in underlying data
    min_date = df["OrderDate"].min()
    max_date = df["OrderDate"].max()
    date_span_days = (max_date - min_date).days if pd.notna(min_date) and pd.notna(max_date) else 0

    # Group first to check periods count
    agg_df = aggregate_time_series(df, selected_frequency)
    if not agg_df.empty:
        agg_df = fill_missing_periods(agg_df, selected_frequency, min_date, max_date)
        aggregated_period_count = len(agg_df)
        non_zero_period_count = int((agg_df["Revenue"] > 0).sum())
    else:
        aggregated_period_count = 0
        non_zero_period_count = 0

    coverage_ratio = (non_zero_period_count / aggregated_period_count) if aggregated_period_count > 0 else 0.0

    # Evaluate UNAVAILABLE checks first
    is_unavailable = False
    if date_span_days < 14:
        reasons.append(f"Date span is too short ({date_span_days} days). Minimum required is 14 days.")
        is_unavailable = True
    if aggregated_period_count < M:
        reasons.append(f"Insufficient aggregated periods count ({aggregated_period_count}). Minimum required for {selected_frequency} frequency is {M}.")
        is_unavailable = True
    if non_zero_period_count < 3:
        reasons.append(f"Fewer than 3 periods with non-zero sales transactions ({non_zero_period_count}).")
        is_unavailable = True
    if coverage_ratio < 0.20:
        reasons.append(f"Observations coverage ratio too low ({coverage_ratio:.2f}). Minimum threshold is 0.20.")
        is_unavailable = True

    if is_unavailable:
        state = "UNAVAILABLE"
    else:
        # Check SUITABLE conditions
        is_suitable = (
            date_span_days >= 45 and
            aggregated_period_count >= (M + H) and
            non_zero_period_count >= 5 and
            coverage_ratio >= 0.50
        )
        if is_suitable:
            state = "SUITABLE"
            reasons.append("Dataset satisfies all parameters for robust forecasting.")
        else:
            state = "LIMITED"
            if date_span_days < 45:
                reasons.append(f"Limited history span: {date_span_days} days. (Suitable threshold: >= 45 days)")
            if aggregated_period_count < (M + H):
                reasons.append(f"Limited period count: {aggregated_period_count}. (Suitable threshold for full holdout: >= {M+H})")
            if non_zero_period_count < 5:
                reasons.append(f"Low transaction frequency: {non_zero_period_count} non-zero periods. (Suitable threshold: >= 5)")
            if coverage_ratio < 0.50:
                reasons.append(f"Sparse database: coverage is {coverage_ratio:.2%}. (Suitable threshold: >= 50%)")

    validation_status = "None (Insufficient History)"
    if state in ["SUITABLE", "LIMITED"]:
        if aggregated_period_count >= M + 1:
            if aggregated_period_count >= M + H:
                validation_status = "Validated (Full)"
            else:
                validation_status = "Validated (Compressed)"

    return {
        "working_row_count": len(df),
        "eligible_row_count": len(df),  # Passed df is prepared already
        "aggregated_period_count": aggregated_period_count,
        "non_zero_period_count": non_zero_period_count,
        "date_span_days": date_span_days,
        "coverage_ratio": coverage_ratio,
        "selected_frequency": selected_frequency,
        "capability_state": state,
        "capability_reasons": reasons,
        "validation_status": validation_status
    }


def fill_missing_periods(df: pd.DataFrame, frequency: str, min_date: datetime, max_date: datetime) -> pd.DataFrame:
    """
    Fills gaps in the calendar timeline based on target frequency.
    Standardizes dates and populates null columns with 0.
    """
    if df.empty or pd.isna(min_date) or pd.isna(max_date):
        return df

    # Normalize bounds based on aggregation
    if frequency == "Monthly":
        start_date = pd.to_datetime(min_date).replace(day=1).normalize()
        end_date = pd.to_datetime(max_date).replace(day=1).normalize()
        freq_str = "MS"
    elif frequency == "Weekly":
        # Monday of weeks
        start_date = pd.to_datetime(min_date) - pd.to_timedelta(pd.to_datetime(min_date).dayofweek, unit='D')
        start_date = start_date.normalize()
        end_date = pd.to_datetime(max_date) - pd.to_timedelta(pd.to_datetime(max_date).dayofweek, unit='D')
        end_date = end_date.normalize()
        freq_str = "W-MON"
    else:  # Daily
        start_date = pd.to_datetime(min_date).normalize()
        end_date = pd.to_datetime(max_date).normalize()
        freq_str = "D"

    # Create total range grid
    full_range = pd.date_range(start=start_date, end=end_date, freq=freq_str)
    
    # Reindex
    work_df = df.copy()
    work_df["Date"] = pd.to_datetime(work_df["Date"]).dt.normalize()
    work_df = work_df.set_index("Date")
    
    # Merge on the date index grid
    work_df = work_df.reindex(full_range)
    work_df.index.name = "Date"
    work_df = work_df.reset_index()
    
    # Fill NAs
    work_df["Revenue"] = work_df["Revenue"].fillna(0.0)
    work_df["Orders"] = work_df["Orders"].fillna(0).astype(int)
    work_df["Units"] = work_df["Units"].fillna(0).astype(int)
    
    return work_df


def calculate_trend_diagnostics(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculates summary diagnostics of history series: slope, PoP growth metrics,
    rolling indices, and volatility metrics.
    """
    if df.empty:
        return {
            "trend_direction": "Neutral",
            "trend_slope": 0.0,
            "period_growth_rate": 0.0,
            "rolling_average_3p": 0.0,
            "historical_volatility": 0.0
        }
    
    revenue = df["Revenue"].values
    n = len(revenue)
    
    # 1. Slope fit
    if n >= 3:
        t = np.arange(1, n + 1)
        t_bar = np.mean(t)
        y_bar = np.mean(revenue)
        slope = np.sum((t - t_bar) * (revenue - y_bar)) / np.sum((t - t_bar)**2)
    else:
        slope = 0.0
        
    trend_dir = "Neutral"
    if slope > 1e-2:
        trend_dir = "Upward"
    elif slope < -1e-2:
        trend_dir = "Downward"

    # 2. Period over Period Growth
    if n >= 2 and revenue[-2] > 0:
        growth = ((revenue[-1] - revenue[-2]) / revenue[-2]) * 100.0
    else:
        growth = 0.0

    # 3. Rolling Average
    last_3 = revenue[-3:] if n >= 3 else revenue
    roll_avg = float(np.mean(last_3)) if len(last_3) > 0 else 0.0

    # 4. Volatility
    vol = float(np.std(revenue)) if n > 0 else 0.0

    return {
        "trend_direction": trend_dir,
        "trend_slope": float(slope),
        "period_growth_rate": float(growth),
        "rolling_average_3p": roll_avg,
        "historical_volatility": vol
    }


def fit_and_predict_model(
    train_y: np.ndarray,
    horizon: int,
    model_type: str,
    frequency: str
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Fits standard model equations on training array and projects forward by horizon steps.
    Returns:
        (predicted_array, in_sample_fitted_array)
    """
    n_train = len(train_y)
    fitted = np.zeros_like(train_y)
    preds = np.zeros(horizon)

    if model_type == "Naive":
        # Forecast matches the last actual value
        last_val = train_y[-1] if n_train > 0 else 0.0
        preds[:] = last_val
        if n_train > 1:
            fitted[1:] = train_y[:-1]
        fitted[0] = train_y[0]

    elif model_type == "Moving Average":
        # MA-3 window parameters
        W = 3
        # Forecast is mean of last 3 values
        last_val = np.mean(train_y[-W:]) if n_train >= W else np.mean(train_y) if n_train > 0 else 0.0
        preds[:] = last_val
        
        # Fit in sample
        for t in range(n_train):
            if t < W:
                fitted[t] = np.mean(train_y[:t+1])
            else:
                fitted[t] = np.mean(train_y[t-W:t])

    elif model_type == "Linear Trend":
        # Linear Regression fit
        t_seq = np.arange(1, n_train + 1)
        if n_train >= 3:
            t_bar = np.mean(t_seq)
            y_bar = np.mean(train_y)
            num = np.sum((t_seq - t_bar) * (train_y - y_bar))
            denom = np.sum((t_seq - t_bar)**2)
            beta_1 = num / denom if denom != 0 else 0.0
            beta_0 = y_bar - beta_1 * t_bar
        else:
            beta_0 = np.mean(train_y) if n_train > 0 else 0.0
            beta_1 = 0.0
            
        # Predictions
        for h in range(1, horizon + 1):
            preds[h-1] = max(0.0, beta_0 + beta_1 * (n_train + h))
            
        # Fitted
        for t in range(n_train):
            fitted[t] = max(0.0, beta_0 + beta_1 * (t + 1))

    elif model_type == "Seasonal Naive":
        # Set seasonal step
        if frequency == "Monthly":
            S = 12
        elif frequency == "Weekly":
            S = 52
        else:  # Daily
            S = 7
            
        # Projections
        for h in range(1, horizon + 1):
            idx = n_train - S + ((h - 1) % S)
            preds[h-1] = train_y[idx] if idx >= 0 else train_y[-1]
            
        # Fitted
        for t in range(n_train):
            if t >= S:
                fitted[t] = train_y[t - S]
            else:
                fitted[t] = train_y[0]
                
    else:
        # Default fallback
        preds[:] = 0.0

    return preds, fitted


def evaluate_seasonal_naive_eligibility(df: pd.DataFrame, frequency: str) -> Tuple[bool, str]:
    """
    Inspects seasonal conditions for Seasonal Naive eligibility.
    Minimum 2 complete seasonal cycles, contiguous grid, and sufficient observations coverage.
    """
    n = len(df)
    if frequency == "Monthly":
        S = 12
    elif frequency == "Weekly":
        S = 52
    else:  # Daily
        S = 7

    if n < 2 * S:
        return False, f"Insufficient history length ({n} periods). Requires at least 2 seasonal cycles ({2 * S} periods)."
    
    # Verify non-zero observations in corresponding season bins
    non_zero = int((df["Revenue"] > 0).sum())
    if non_zero < n * 0.4:
        return False, f"Too few non-zero observations ({non_zero}/{n}). Minimum required is 40%."

    return True, "Eligible"


def evaluate_models(df: pd.DataFrame, frequency: str, capability_state: str) -> Dict[str, Any]:
    """
    Splits data chronologically and evaluates eligible models.
    Determines metric parameters and resolves winner details.
    """
    aggregated_periods = len(df)
    
    # Configure horizon constraints
    if frequency == "Monthly":
        M, H = 6, 3
    elif frequency == "Weekly":
        M, H = 8, 4
    else:  # Daily
        M, H = 14, 7

    # Decide validation check parameters
    if capability_state == "UNAVAILABLE" or aggregated_periods < M + 1:
        return {
            "validation_status": "None (Insufficient History)",
            "best_model": None,
            "metrics": {},
            "comparisons": []
        }

    # Determine validation horizon size
    if aggregated_periods >= M + H:
        H_val = H
        val_status = "Validated (Full)"
    else:
        H_val = aggregated_periods - M
        val_status = "Validated (Compressed)"

    # Split
    y = df["Revenue"].values
    train_y = y[:-H_val]
    val_y = y[-H_val:]

    # Evaluate models
    model_options = ["Naive", "Moving Average", "Linear Trend"]
    
    # Check Seasonal Naive
    s_naive_eligible, s_naive_reason = evaluate_seasonal_naive_eligibility(df, frequency)
    if s_naive_eligible:
        model_options.append("Seasonal Naive")

    comparisons = []
    
    for model in model_options:
        # Check training size constraints specific to models
        if model == "Moving Average" and len(train_y) < 3:
            continue
        if model == "Linear Trend" and len(train_y) < 3:
            continue
            
        preds, fitted = fit_and_predict_model(train_y, H_val, model, frequency)
        
        # Calculate regression markers
        errors = val_y - preds
        mae = float(np.mean(np.abs(errors)))
        rmse = float(np.sqrt(np.mean(errors**2)))
        
        y_sum = np.sum(val_y)
        if y_sum == 0:
            wape = None
        else:
            wape = float(np.sum(np.abs(errors)) / y_sum)
            
        comparisons.append({
            "model": model,
            "WAPE": wape,
            "MAE": mae,
            "RMSE": rmse,
            "is_seasonal_eligible": True if model != "Seasonal Naive" else s_naive_eligible,
            "seasonal_reason": "Eligible" if model != "Seasonal Naive" else s_naive_reason
        })

    if not comparisons:
        return {
            "validation_status": val_status,
            "best_model": None,
            "metrics": {},
            "comparisons": []
        }

    # 1. Zero check
    all_zero_target = (np.sum(val_y) == 0)
    if all_zero_target:
        val_status = "Validated (WAPE Unavailable — Zero Target)"

    # Winner tie breaker algorithm
    # Step A: Filter candidates with valid WAPE
    valid_wape_candidates = [c for c in comparisons if c["WAPE"] is not None]
    
    best_candidate = None
    if valid_wape_candidates:
        # Sort by WAPE
        best_candidate = min(valid_wape_candidates, key=lambda x: x["WAPE"])
        # Handle ties
        ties = [c for c in valid_wape_candidates if c["WAPE"] == best_candidate["WAPE"]]
        if len(ties) > 1:
            # Tie break priority: Seasonal Naive > Linear Trend > Moving Average > Naive
            priority = {"Seasonal Naive": 0, "Linear Trend": 1, "Moving Average": 2, "Naive": 3}
            best_candidate = min(ties, key=lambda x: priority.get(x["model"], 4))
    else:
        # Step B: Fallback to MAE ranking
        best_candidate = min(comparisons, key=lambda x: x["MAE"])
        ties = [c for c in comparisons if c["MAE"] == best_candidate["MAE"]]
        if len(ties) > 1:
            best_candidate = min(ties, key=lambda x: x["RMSE"])
            tb_ties = [c for c in ties if c["RMSE"] == best_candidate["RMSE"]]
            if len(tb_ties) > 1:
                priority = {"Seasonal Naive": 0, "Linear Trend": 1, "Moving Average": 2, "Naive": 3}
                best_candidate = min(tb_ties, key=lambda x: priority.get(x["model"], 4))

    return {
        "validation_status": val_status,
        "best_model": best_candidate["model"] if best_candidate else None,
        "metrics": {
            "WAPE": best_candidate["WAPE"] if best_candidate else None,
            "MAE": best_candidate["MAE"] if best_candidate else 0.0,
            "RMSE": best_candidate["RMSE"] if best_candidate else 0.0
        },
        "comparisons": comparisons
    }


def generate_forecast(df: pd.DataFrame, frequency: str, horizon: int, capability_state: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Fits elected model on complete timeline and projects forward.
    Calculates residual-based prediction error intervals.
    Returns:
        (results_df, metadata)
    """
    n = len(df)
    
    # Re-evaluate models to decide training winner
    val_info = evaluate_models(df, frequency, capability_state)
    
    # Resolve Model Selection: Validated Path vs Unvalidated Fallback
    if capability_state == "UNAVAILABLE":
        # Fallback projection
        selected_model = "Moving Average" if n >= 3 else "Naive"
        model_display_name = f"Fallback Baseline (Unvalidated Projection)"
        validation_status = "None (Insufficient History)"
        is_validated = False
    else:
        # Check path
        if val_info.get("best_model") is not None:
            selected_model = val_info["best_model"]
            model_display_name = selected_model
            validation_status = val_info["validation_status"]
            is_validated = True
        else:
            # Fallback path if validation couldn't run due to training constraints
            selected_model = "Moving Average" if n >= 3 else "Naive"
            model_display_name = f"Fallback Baseline (Unvalidated Projection)"
            validation_status = "None (Insufficient History)"
            is_validated = False

    # Fit selected model on ENTIRE series
    y_full = df["Revenue"].values
    preds, fitted = fit_and_predict_model(y_full, horizon, selected_model, frequency)

    # In-sample residuals std error
    residuals = y_full - fitted
    dof = 1 if selected_model in ["Naive", "Moving Average"] else 2 if selected_model == "Linear Trend" else 0
    den = len(residuals) - dof
    if den > 0:
        se = np.sqrt(np.sum(residuals**2) / den)
    else:
        se = float(np.std(residuals)) if len(residuals) > 0 else 0.0

    # Project intervals
    future_rows = []
    last_date = df["Date"].max()

    # Determine date range multiplier
    if frequency == "Monthly":
        freq_offset = pd.offsets.MonthBegin(1)
    elif frequency == "Weekly":
        freq_offset = pd.offsets.Week(1, weekday=0) # Monday
    else:
        freq_offset = pd.offsets.Day(1)

    for h in range(1, horizon + 1):
        future_date = last_date + (freq_offset * h)
        pred_rev = max(0.0, preds[h-1])
        
        # Uncertainty width increases with target horizon step
        width = 1.96 * se * np.sqrt(h)
        lower = max(0.0, pred_rev - width)
        upper = pred_rev + width
        
        future_rows.append({
            "Date": future_date,
            "ActualRevenue": np.nan,
            "PredictedRevenue": float(pred_rev),
            "LowerBound": float(lower),
            "UpperBound": float(upper),
            "IsForecast": True
        })

    # Prepare historical rows output (ensure bounds and predictions are null)
    history_rows = []
    for idx, row in df.iterrows():
        history_rows.append({
            "Date": row["Date"],
            "ActualRevenue": float(row["Revenue"]),
            "PredictedRevenue": np.nan,
            "LowerBound": np.nan,
            "UpperBound": np.nan,
            "IsForecast": False
        })

    # Combine
    results_df = pd.DataFrame(history_rows + future_rows)
    results_df["Date"] = pd.to_datetime(results_df["Date"])
    
    # Metadata construction
    # Count variables
    non_zero = int((y_full > 0).sum())
    coverage = (non_zero / n) if n > 0 else 0.0
    min_date = df["Date"].min()
    max_date = df["Date"].max()
    span = (max_date - min_date).days if pd.notna(min_date) and pd.notna(max_date) else 0

    s_naive_eligible, s_naive_reason = evaluate_seasonal_naive_eligibility(df, frequency)

    meta_out = {
        "working_row_count": n,
        "eligible_row_count": n,
        "aggregated_period_count": n,
        "non_zero_period_count": non_zero,
        "date_span_days": span,
        "coverage_ratio": coverage,
        "selected_frequency": frequency,
        "capability_state": capability_state,
        "capability_reasons": ["Forecasting executed successfully"],
        "validation_status": validation_status,
        "is_validated": is_validated,
        "selected_model": selected_model,
        "model_display_name": model_display_name,
        "uncertainty_basis": "Empirical Standard Error of Residuals (expanding over timestep h)",
        "diagnostics": calculate_trend_diagnostics(df),
        "validation_metrics": val_info.get("metrics") if is_validated else None,
        "model_comparisons": val_info.get("comparisons", []),
        "seasonal_naive_eligibility": {
            "eligible": s_naive_eligible,
            "reason": s_naive_reason
        }
    }

    return results_df, meta_out
