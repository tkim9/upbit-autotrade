import os
import sqlite3

import pandas as pd
import streamlit as st

from src.functions.sql_db import DB_PATH


def load_trade_diary_entries(db_path: str) -> tuple[pd.DataFrame, str | None]:
    """Load trade diary entries in read-only mode."""
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

        df = pd.read_sql_query(
            """
            SELECT timestamp, reflection_timestamp, decision, reflection
            FROM trading_decisions
            WHERE reflection IS NOT NULL
              AND TRIM(reflection) <> ''
            """,
            conn,
        )
        conn.close()
    except sqlite3.Error as exc:
        return pd.DataFrame(), f"Failed to read database: {exc}"

    if df.empty:
        return df, None

    df["timestamp_dt"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["reflection_timestamp_dt"] = pd.to_datetime(df["reflection_timestamp"], errors="coerce")
    df["sort_dt"] = df["reflection_timestamp_dt"].combine_first(df["timestamp_dt"])
    df = df.sort_values(by="sort_dt", ascending=False, na_position="last")

    df["Date"] = df["timestamp_dt"].dt.strftime("%Y-%m-%d %H:%M:%S")
    fallback_date = df["sort_dt"].dt.strftime("%Y-%m-%d %H:%M:%S")
    df["Date"] = df["Date"].fillna(fallback_date).fillna("-")
    df["Decision"] = df["decision"].fillna("unknown").astype(str).str.upper()
    df["Reflection"] = df["reflection"].fillna("").astype(str)

    return df[["Date", "Decision", "Reflection"]], None


def main() -> None:
    st.set_page_config(page_title="Trade Diary", page_icon=":book:", layout="wide")
    st.title("Trade Diary")
    st.caption("Latest reflection appears first. Data is read-only from trading_decisions.")

    df, error = load_trade_diary_entries(DB_PATH)
    if error:
        st.warning(error)
        return

    if df.empty:
        st.info("No reflections found yet in 'trading_decisions'.")
        return

    st.caption(f"DB path: {DB_PATH}")
    st.caption(f"Last refreshed: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.markdown("### Diary Entries")
    st.caption("Newest entries appear first.")

    for entry in df.itertuples(index=False):
        st.markdown(
            f"**{entry.Date}**  \n"
            f"*Decision: {entry.Decision}*"
        )
        st.markdown(entry.Reflection)
        st.markdown("---")


if __name__ == "__main__":
    main()
