import os
import sqlite3
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from src.functions.sql_db import DB_PATH


def load_trading_decisions(db_path: str) -> tuple[pd.DataFrame, str | None]:
    """Load trading_decisions as a DataFrame in read-only mode."""
    if not os.path.exists(db_path):
        return pd.DataFrame(), f"Database not found: {db_path}"

    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        table_exists = pd.read_sql_query(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='trading_decisions';",
            conn,
        )
        if table_exists.empty:
            conn.close()
            return pd.DataFrame(), "Table 'trading_decisions' does not exist yet."

        df = pd.read_sql_query("SELECT * FROM trading_decisions", conn)
        conn.close()
    except sqlite3.Error as exc:
        return pd.DataFrame(), f"Failed to read database: {exc}"

    if df.empty:
        return df, None

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    if "is_real_trade" in df.columns:
        df["is_real_trade"] = pd.to_numeric(df["is_real_trade"], errors="coerce")
    if "confidence_score" in df.columns:
        df["confidence_score"] = pd.to_numeric(df["confidence_score"], errors="coerce")
    if "profit_loss" in df.columns:
        df["profit_loss"] = pd.to_numeric(df["profit_loss"], errors="coerce")

    return df, None


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    st.sidebar.header("Filters")

    coin_options = sorted(df["coin_name"].dropna().astype(str).unique().tolist())
    selected_coins = st.sidebar.multiselect(
        "Coins to include",
        options=coin_options,
        default=coin_options,
    )

    timestamp_series = df["timestamp"].dropna()
    if timestamp_series.empty:
        start_date = end_date = date.today()
        date_range = st.sidebar.date_input("Date range", value=(start_date, end_date))
    else:
        min_date = timestamp_series.min().date()
        max_date = timestamp_series.max().date()
        date_range = st.sidebar.date_input("Date range", value=(min_date, max_date))

    trade_mode = st.sidebar.multiselect(
        "Trade type",
        options=["Real", "Simulated", "Unknown"],
        default=["Real", "Simulated", "Unknown"],
    )

    filtered = df.copy()

    if selected_coins:
        filtered = filtered[filtered["coin_name"].isin(selected_coins)]
    else:
        return pd.DataFrame(columns=df.columns)

    if isinstance(date_range, tuple) and len(date_range) == 2:
        start, end = date_range
        filtered = filtered[
            filtered["timestamp"].notna()
            & (filtered["timestamp"].dt.date >= start)
            & (filtered["timestamp"].dt.date <= end)
        ]

    allowed_real_values = []
    if "Real" in trade_mode:
        allowed_real_values.append(1)
    if "Simulated" in trade_mode:
        allowed_real_values.append(0)
    if "Unknown" in trade_mode:
        filtered_unknown = filtered[filtered["is_real_trade"].isna()]
    else:
        filtered_unknown = pd.DataFrame(columns=filtered.columns)

    filtered_known = filtered[filtered["is_real_trade"].isin(allowed_real_values)]
    filtered = pd.concat([filtered_known, filtered_unknown], ignore_index=True)

    return filtered.sort_values(by="timestamp", ascending=False, na_position="last")


def render_portfolio_pie(df: pd.DataFrame) -> None:
    st.subheader("Portfolio Balance")
    required_cols = {"coin_name", "coin_balance", "coin_krw_price", "krw_balance"}
    if not required_cols.issubset(df.columns):
        st.info("Portfolio chart unavailable (required balance columns are missing).")
        return

    latest_by_coin = (
        df.sort_values(by="timestamp", ascending=False, na_position="last")
        .dropna(subset=["coin_name"])
        .groupby("coin_name", as_index=False)
        .first()
    )

    latest_by_coin["coin_balance"] = pd.to_numeric(latest_by_coin["coin_balance"], errors="coerce")
    latest_by_coin["coin_krw_price"] = pd.to_numeric(latest_by_coin["coin_krw_price"], errors="coerce")
    latest_by_coin["value_krw"] = latest_by_coin["coin_balance"] * latest_by_coin["coin_krw_price"]
    coin_values = latest_by_coin[["coin_name", "value_krw"]].dropna()
    # Ignore dust-size assets so chart reflects practical portfolio composition.
    coin_values = coin_values[coin_values["value_krw"] >= 1.0]
    coin_values = coin_values.rename(columns={"coin_name": "asset"})

    latest_cash = (
        pd.to_numeric(df["krw_balance"], errors="coerce")
        .dropna()
        .head(1)
    )
    cash_value = float(latest_cash.iloc[0]) if not latest_cash.empty else 0.0

    pie_df = coin_values.copy()
    if cash_value > 0:
        pie_df = pd.concat(
            [pie_df, pd.DataFrame([{"asset": "KRW", "value_krw": cash_value}])],
            ignore_index=True,
        )

    if pie_df.empty:
        st.info("No valid portfolio balance data is available for the selected filters.")
        return

    fig = px.pie(
        pie_df,
        names="asset",
        values="value_krw",
        title="Portfolio Composition (KRW Value)",
    )
    fig.update_traces(
        textposition="inside",
        texttemplate="%{label}<br>%{percent:.2%}<br>%{value:,.2f} KRW",
        hovertemplate="%{label}: %{value:,.2f} KRW (%{percent:.2%})<extra></extra>",
    )
    st.plotly_chart(fig, use_container_width=True)

    total_value = float(pie_df["value_krw"].sum())
    krw_percent = (cash_value / total_value * 100) if total_value > 0 else 0.0
    st.caption(f"Current KRW balance: {cash_value:,.2f} KRW ({krw_percent:.2f}% of filtered portfolio)")


def render_kpis(df: pd.DataFrame) -> None:
    total = len(df)
    buy_count = int((df["decision"] == "buy").sum()) if "decision" in df.columns else 0
    sell_count = int((df["decision"] == "sell").sum()) if "decision" in df.columns else 0
    hold_count = int((df["decision"] == "hold").sum()) if "decision" in df.columns else 0

    real_count = int((df["is_real_trade"] == 1).sum()) if "is_real_trade" in df.columns else 0
    sim_count = int((df["is_real_trade"] == 0).sum()) if "is_real_trade" in df.columns else 0

    avg_conf = (
        float(df["confidence_score"].mean())
        if "confidence_score" in df.columns and df["confidence_score"].notna().any()
        else None
    )

    reflection_available = (
        df["reflection"].fillna("").astype(str).str.strip() != ""
        if "reflection" in df.columns
        else pd.Series(dtype=bool)
    )
    reflected_count = int(reflection_available.sum()) if len(reflection_available) else 0

    avg_profit = (
        float(df["profit_loss"].mean())
        if "profit_loss" in df.columns and df["profit_loss"].notna().any()
        else None
    )

    result_series = (
        df["result_type"].fillna("").astype(str).str.strip().str.lower()
        if "result_type" in df.columns
        else pd.Series(dtype=str)
    )
    valid_results = result_series[result_series != ""]
    win_rate = (
        float((valid_results == "gain").mean() * 100)
        if not valid_results.empty
        else None
    )

    row1 = st.columns(4)
    row1[0].metric("Total records", f"{total}")
    row1[1].metric("Buy / Sell / Hold", f"{buy_count} / {sell_count} / {hold_count}")
    row1[2].metric("Real / Simulated", f"{real_count} / {sim_count}")
    row1[3].metric("Avg confidence", "-" if avg_conf is None else f"{avg_conf:.1f}")

    row2 = st.columns(3)
    row2[0].metric("Reflections generated", f"{reflected_count}")
    row2[1].metric("Avg profit_loss", "-" if avg_profit is None else f"{avg_profit:.2%}")
    row2[2].metric("Win rate (result_type)", "-" if win_rate is None else f"{win_rate:.1f}%")


def render_charts_and_table(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("No rows match current filters.")
        return

    col1, col2 = st.columns(2)

    with col1:
        decision_counts = (
            df["decision"]
            .fillna("unknown")
            .astype(str)
            .value_counts()
            .rename_axis("decision")
            .reset_index(name="count")
        )
        fig_decision = px.bar(
            decision_counts,
            x="decision",
            y="count",
            title="Decision Distribution",
        )
        st.plotly_chart(fig_decision, use_container_width=True)

    with col2:
        timeline_source = df[df["timestamp"].notna()].copy()
        if timeline_source.empty:
            st.info("Timeline unavailable (no valid timestamps).")
        else:
            timeline_source["date"] = timeline_source["timestamp"].dt.date
            timeline = timeline_source.groupby("date").size().reset_index(name="count")
            fig_timeline = px.line(
                timeline,
                x="date",
                y="count",
                markers=True,
                title="Decisions Over Time",
            )
            st.plotly_chart(fig_timeline, use_container_width=True)

    st.subheader("Recent Decisions")
    display_cols = [
        "timestamp",
        "coin_name",
        "decision",
        "confidence_score",
        "profit_loss",
        "is_real_trade",
    ]
    cols = [col for col in display_cols if col in df.columns]
    recent = df[cols].sort_values(by="timestamp", ascending=False, na_position="last").head(50).copy()

    if "timestamp" in recent.columns:
        recent["timestamp"] = recent["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    if "is_real_trade" in recent.columns:
        recent["is_real_trade"] = recent["is_real_trade"].map({1: "Real", 0: "Simulated"}).fillna("Unknown")

    st.dataframe(recent, use_container_width=True, hide_index=True)


def main() -> None:
    st.set_page_config(page_title="Trade Dashboard", page_icon=":bar_chart:", layout="wide")
    st.title("Trading Summary Dashboard")
    st.caption("Read-only landing page for trade statistics. No trade execution is performed here.")

    df, error = load_trading_decisions(DB_PATH)
    if error:
        st.warning(error)
        return

    if df.empty:
        st.info("No trading records found yet in 'trading_decisions'.")
        return

    st.caption(f"DB path: {DB_PATH}")
    st.caption(f"Last refreshed: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")

    filtered = apply_filters(df)
    render_kpis(filtered)
    st.divider()
    render_portfolio_pie(filtered)
    st.divider()
    render_charts_and_table(filtered)


if __name__ == "__main__":
    main()
