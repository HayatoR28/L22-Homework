# No Ai was used in the development of my code, looked at our powerpoints for help mostly.
# Name: Hayato Rodriguez
# Student ID: U0000018956

import pandas as pd
import requests
import streamlit as st


BASE_URL = "https://api.coingecko.com/api/v3"


@st.cache_data(ttl=600)
def fetch_api_json(endpoint: str, params: dict):
    """Fetch JSON data from CoinGecko with graceful error handling."""
    try:
        response = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=20)
        response.raise_for_status()
        return response.json(), None
    except requests.exceptions.RequestException as exc:
        return None, str(exc)


def build_market_chart_dataframe(raw_chart: dict) -> pd.DataFrame:
    prices = raw_chart.get("prices", [])
    rows = [{"timestamp": item[0], "price": item[1]} for item in prices]
    chart_df = pd.DataFrame(rows)
    if chart_df.empty:
        return chart_df

    chart_df["timestamp"] = pd.to_datetime(chart_df["timestamp"], unit="ms")
    chart_df = chart_df.sort_values("timestamp").reset_index(drop=True)
    return chart_df


def build_markets_dataframe(raw_markets: list) -> pd.DataFrame:
    markets_df = pd.DataFrame(raw_markets)
    if markets_df.empty:
        return markets_df

    keep_cols = [
        "id",
        "symbol",
        "name",
        "current_price",
        "market_cap",
        "market_cap_rank",
        "total_volume",
        "price_change_percentage_24h",
    ]
    existing_cols = [col for col in keep_cols if col in markets_df.columns]
    markets_df = markets_df[existing_cols].copy()
    markets_df = markets_df.sort_values("market_cap", ascending=False).reset_index(drop=True)
    return markets_df


def main():
    st.set_page_config(page_title="Crypto Dashboard", page_icon="C", layout="wide")

    st.title("Interactive Crypto Dashboard")
    st.caption("Live market data powered by CoinGecko")

    st.sidebar.header("Controls")
    vs_currency = st.sidebar.selectbox("Currency", options=["usd", "eur", "jpy"])
    top_n = st.sidebar.slider("Number of Coins", min_value=5, max_value=50, value=20, step=5)
    days = st.sidebar.slider("Time Series Window (days)", min_value=1, max_value=90, value=30)

    markets_params = {
        "vs_currency": vs_currency,
        "order": "market_cap_desc",
        "per_page": top_n,
        "page": 1,
        "sparkline": "false",
        "price_change_percentage": "24h",
    }
    raw_markets, markets_err = fetch_api_json("coins/markets", markets_params)
    if markets_err:
        st.error(f"Markets request failed: {markets_err}")
        st.stop()

    markets_df = build_markets_dataframe(raw_markets)
    if markets_df.empty:
        st.error("Coin market data was returned, but no usable rows were found.")
        st.stop()

    coin_options = markets_df["id"].tolist()
    selected_coin = st.sidebar.selectbox("Coin", options=coin_options, index=0)

    chart_params = {"vs_currency": vs_currency, "days": days}
    raw_chart, chart_err = fetch_api_json(f"coins/{selected_coin}/market_chart", chart_params)
    if chart_err:
        st.error(f"Time series request failed: {chart_err}")
        st.stop()

    chart_df = build_market_chart_dataframe(raw_chart)
    if chart_df.empty:
        st.error("Time series data was returned, but no usable rows were found.")
        st.stop()

    selected_row = markets_df[markets_df["id"] == selected_coin].iloc[0]
    currency_label = vs_currency.upper()

    col1, col2, col3 = st.columns(3)
    col1.metric("Current Price", f"{selected_row['current_price']:,.4f} {currency_label}")
    col2.metric("24h Change", f"{selected_row['price_change_percentage_24h']:.2f}%")
    col3.metric("Market Cap Rank", f"#{int(selected_row['market_cap_rank'])}")

    st.subheader("Price Time Series")

    ts_df = chart_df.set_index("timestamp")[["price"]]
    st.line_chart(ts_df)

    st.subheader("Top Coins by Market Cap")

    bar_df = markets_df.head(10).set_index("name")[["market_cap"]]
    st.bar_chart(bar_df)

    st.subheader("Market Data Table")

    display_df = markets_df.copy()
    st.dataframe(display_df, use_container_width=True)

    st.markdown("Tip: Change coin, currency, and day window in the sidebar to compare trends.")


if __name__ == "__main__":
    main()