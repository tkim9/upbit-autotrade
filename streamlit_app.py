import streamlit as st


def _switch_page_with_fallback(page_candidates: list[str]) -> tuple[bool, str | None]:
    """Try several page identifiers for broad Streamlit version compatibility."""
    last_error: Exception | None = None
    for candidate in page_candidates:
        try:
            st.switch_page(candidate)
            return True, None
        except Exception as exc:  # pragma: no cover - depends on Streamlit runtime behavior
            last_error = exc
    err = str(last_error) if last_error else "Unknown navigation error."
    return False, err


def main() -> None:
    st.set_page_config(page_title="Navigation:", page_icon=":bar_chart:", layout="wide")
    ok, err = _switch_page_with_fallback(
        [
            "Summary Dashboard",
            "Trading Summary Dashboard",
        ]
    )
    if ok:
        st.stop()

    st.title("Dashboard Navigation")
    st.warning("Failed to open Summary Dashboard automatically.")
    st.info(f"Navigation error: {err}")
    if st.button("Open Summary Dashboard", use_container_width=True):
        ok_btn, err_btn = _switch_page_with_fallback(
            [
                "pages/Summary_Dashboard.py",
                "Summary_Dashboard.py",
                "Summary Dashboard",
                "Trading Summary Dashboard",
            ]
        )
        if not ok_btn:
            st.error(f"Summary navigation failed: {err_btn}")
    if st.button("Open Trade Diary", use_container_width=True):
        ok_btn, err_btn = _switch_page_with_fallback(
            [
                "pages/Trade_Diary.py",
                "Trade_Diary.py",
                "Trade Diary",
            ]
        )
        if not ok_btn:
            st.error(f"Diary navigation failed: {err_btn}")


if __name__ == "__main__":
    main()
