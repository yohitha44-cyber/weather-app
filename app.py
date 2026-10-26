import pandas as pd
import requests
import streamlit as st

GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

WEATHER_CODES = {
    0: ("Clear sky", "☀️"),
    1: ("Mainly clear", "🌤️"),
    2: ("Partly cloudy", "⛅"),
    3: ("Overcast", "☁️"),
    45: ("Fog", "🌫️"),
    48: ("Fog", "🌫️"),
    51: ("Light drizzle", "🌦️"),
    53: ("Drizzle", "🌦️"),
    55: ("Heavy drizzle", "🌦️"),
    61: ("Light rain", "🌧️"),
    63: ("Rain", "🌧️"),
    65: ("Heavy rain", "🌧️"),
    71: ("Light snow", "🌨️"),
    73: ("Snow", "🌨️"),
    75: ("Heavy snow", "❄️"),
    80: ("Rain showers", "🌦️"),
    81: ("Rain showers", "🌧️"),
    82: ("Violent showers", "⛈️"),
    95: ("Thunderstorm", "⛈️"),
    96: ("Thunderstorm + hail", "⛈️"),
    99: ("Thunderstorm + hail", "⛈️"),
}


def describe(code):
    return WEATHER_CODES.get(code, ("Unknown", "❓"))


@st.cache_data(ttl=600)
def search_city(name, country_code=None):
    params = {
        "name": name,
        "count": 100,
        "language": "en",
        "format": "json",
    }

    if country_code:
        params["countryCode"] = country_code

    response = requests.get(
        GEO_URL,
        params=params,
        timeout=15,
    )
    response.raise_for_status()

    return response.json().get("results", [])


@st.cache_data(ttl=600)
def get_weather(lat, lon):
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": (
            "temperature_2m,relative_humidity_2m,"
            "apparent_temperature,wind_speed_10m,weather_code"
        ),
        "daily": (
            "weather_code,temperature_2m_max,"
            "temperature_2m_min,precipitation_probability_max"
        ),
        "timezone": "auto",
        "forecast_days": 7,
    }

    response = requests.get(
        WEATHER_URL,
        params=params,
        timeout=15,
    )
    response.raise_for_status()

    return response.json()


def build_forecast_df(daily):
    rows = []

    for i, day in enumerate(daily["time"]):
        text, icon = describe(daily["weather_code"][i])

        rows.append({
            "Date": pd.to_datetime(day).strftime("%a, %d %b"),
            "Weather": f"{icon} {text}",
            "Min °C": daily["temperature_2m_min"][i],
            "Max °C": daily["temperature_2m_max"][i],
            "Rain %": daily["precipitation_probability_max"][i],
        })

    return pd.DataFrame(rows)


def main():
    st.set_page_config(
        page_title="Worldwide Weather App",
        page_icon="🌦️",
        layout="wide",
    )

    st.title("🌦️ Worldwide Weather App")
    st.write("Search for cities and places in India or worldwide.")

    region = st.radio(
        "🌍 Select search region",
        ["Worldwide", "India"],
        horizontal=True,
    )

    city = st.text_input(
        "🔍 Enter city / town / place name",
        value="Chennai",
        placeholder="Example: Chennai, London, Tokyo, New York",
    )

    if len(city.strip()) < 2:
        st.info("Please enter at least 2 characters.")
        return

    country_code = "IN" if region == "India" else None

    try:
        with st.spinner("Searching locations..."):
            places = search_city(city.strip(), country_code)

    except requests.RequestException:
        st.error("Unable to search locations. Check your internet connection.")
        return

    if not places:
        st.warning(
            "No matching places found. Try another name or spelling."
        )
        return

    labels = []

    for p in places:
        parts = [
            p.get("name"),
            p.get("admin2"),
            p.get("admin1"),
            p.get("country"),
        ]

        label = ", ".join(
            dict.fromkeys(
                part.strip()
                for part in parts
                if isinstance(part, str) and part.strip()
            )
        )

        labels.append(label)

    st.success(f"Found {len(places)} matching locations.")

    choice = st.selectbox(
        "📍 Select your place",
        range(len(places)),
        format_func=lambda i: labels[i],
    )

    place = places[choice]

    st.caption(
        f"Latitude: {place['latitude']} | "
        f"Longitude: {place['longitude']} | "
        f"Timezone: {place.get('timezone', 'Unknown')}"
    )

    try:
        with st.spinner("Loading weather data..."):
            data = get_weather(
                place["latitude"],
                place["longitude"],
            )

    except requests.RequestException:
        st.error("Unable to load weather data. Please try again.")
        return

    cur = data["current"]
    text, icon = describe(cur["weather_code"])

    st.divider()
    st.header(f"{icon} {place['name']} — {text}")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "🌡️ Temperature",
        f"{cur['temperature_2m']} °C",
    )
    c2.metric(
        "🤔 Feels like",
        f"{cur['apparent_temperature']} °C",
    )
    c3.metric(
        "💧 Humidity",
        f"{cur['relative_humidity_2m']}%",
    )
    c4.metric(
        "💨 Wind speed",
        f"{cur['wind_speed_10m']} km/h",
    )

    st.caption(f"Last updated: {cur['time']} (local time)")

    st.divider()
    st.subheader("📅 7-Day Weather Forecast")

    df = build_forecast_df(data["daily"])

    st.dataframe(
        df,
        hide_index=True,
        use_container_width=True,
    )

    st.subheader("📈 Temperature Forecast")

    st.line_chart(
        df.set_index("Date")[["Min °C", "Max °C"]]
    )

    st.caption("Weather data provided by Open-Meteo.")


if __name__ == "__main__":
    main()