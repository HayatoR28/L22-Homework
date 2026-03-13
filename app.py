# No Ai was used in the development of my code, looked at our powerpoints for help mostly.
# Name: Hayato Rodriguez
# Student ID: U0000018956

from datetime import datetime

import pandas as pd
import requests
import streamlit as st


BASE_URL = "https://api.openweathermap.org/data/2.5"


@st.cache_data(ttl=600)
def fetch_api_json(endpoint: str, params: dict):
    """Fetch JSON data from OpenWeatherMap with graceful error handling."""
    try:
        response = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=15)
        response.raise_for_status()
        return response.json(), None
    except requests.exceptions.RequestException as exc:
        return None, str(exc)


def get_api_key():
    if "OPENWEATHER_API_KEY" not in st.secrets:
        return None
    return st.secrets["OPENWEATHER_API_KEY"]


def build_forecast_dataframe(raw_forecast: dict) -> pd.DataFrame:
    rows = []
    for item in raw_forecast.get("list", []):
        rows.append(
            {
                "timestamp": datetime.fromtimestamp(item["dt"]),
                "temperature": item["main"].get("temp"),
                "feels_like": item["main"].get("feels_like"),
                "humidity": item["main"].get("humidity"),
                "weather": item["weather"][0].get("main", "Unknown"),
                "description": item["weather"][0].get("description", "Unknown"),
                "wind_speed": item["wind"].get("speed"),
                "clouds": item.get("clouds", {}).get("all"),
            }
        )

    forecast_df = pd.DataFrame(rows)
    if not forecast_df.empty:
        forecast_df = forecast_df.sort_values("timestamp").reset_index(drop=True)
    return forecast_df


def main():
    st.set_page_config(page_title="Weather Dashboard", page_icon="W", layout="wide")

    st.title("Interactive Weather Dashboard")
    st.caption("Live weather and forecast data powered by OpenWeatherMap")

    api_key = get_api_key()
    if not api_key:
        st.error(
            "Missing OPENWEATHER_API_KEY in Streamlit secrets. "
            "Add it in .streamlit/secrets.toml locally and in Streamlit Cloud settings."
        )
        st.stop()

    st.sidebar.header("Controls")
    city = st.sidebar.text_input("City", value="Orlando")
    units = st.sidebar.selectbox(
        "Units",
        options=["metric", "imperial", "standard"],
        format_func=lambda u: {
            "metric": "Metric (Celsius)",
            "imperial": "Imperial (Fahrenheit)",
            "standard": "Standard (Kelvin)",
        }[u],
    )
    forecast_days = st.sidebar.slider("Forecast Window (days)", min_value=1, max_value=5, value=3)

    unit_symbol = {"metric": "C", "imperial": "F", "standard": "K"}[units]
    speed_unit = {"metric": "m/s", "imperial": "mph", "standard": "m/s"}[units]

    current_params = {"q": city, "appid": api_key, "units": units}
    forecast_params = {"q": city, "appid": api_key, "units": units}

    current_data, current_err = fetch_api_json("weather", current_params)
    forecast_data, forecast_err = fetch_api_json("forecast", forecast_params)

    if current_err:
        st.error(f"Current weather request failed: {current_err}")
        st.stop()
    if forecast_err:
        st.error(f"Forecast request failed: {forecast_err}")
        st.stop()

    forecast_df = build_forecast_dataframe(forecast_data)
    if forecast_df.empty:
        st.error("Forecast data was returned, but no usable rows were found.")
        st.stop()

    end_time = forecast_df["timestamp"].min() + pd.Timedelta(days=forecast_days)
    filtered_df = forecast_df[forecast_df["timestamp"] <= end_time].copy()
    if filtered_df.empty:
        st.error("No forecast data available in the selected time window.")
        st.stop()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        "Current Temp",
        f"{current_data['main']['temp']:.1f} {unit_symbol}",
        delta=f"{current_data['main']['temp'] - filtered_df['temperature'].iloc[0]:.1f} vs next forecast",
    )
    col2.metric("Feels Like", f"{current_data['main']['feels_like']:.1f} {unit_symbol}")
    col3.metric("Humidity", f"{current_data['main']['humidity']}%")
    col4.metric("Wind", f"{current_data['wind']['speed']:.1f} {speed_unit}")

    st.subheader("5-Day Forecast Time Series")

    ts_df = filtered_df.set_index("timestamp")[["temperature", "feels_like"]]
    st.line_chart(ts_df)

    st.subheader("Average Temperature by Day")

    daily_df = filtered_df.copy()
    daily_df["date"] = daily_df["timestamp"].dt.date
    daily_avg = daily_df.groupby("date", as_index=False)["temperature"].mean()
    daily_avg = daily_avg.set_index("date")
    st.bar_chart(daily_avg)

    st.subheader("Forecast Data Table")

    display_df = filtered_df.copy()
    display_df["timestamp"] = display_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M")
    st.dataframe(display_df, use_container_width=True)

    st.markdown(
        "Tip: Change city, units, and forecast window in the sidebar to compare trends."
    )


if __name__ == "__main__":
    main()