"""
Farm Analytics – Streamlit App
Weather + Forecast + Extreme Events + Interactive Visualizations + Farmer Report + Flood Analysis
"""

import streamlit as st
import pandas as pd
import requests
from datetime import date, timedelta
import plotly.express as px

# =====================
# LOCATION FUNCTION
# =====================
def get_user_location():
    try:
        res = requests.get("https://ipapi.co/json/", timeout=10)
        if res.status_code == 200:
            data = res.json()
            return data["latitude"], data["longitude"], data.get("city", "Unknown")
        else:
            return None, None, None
    except Exception:
        return None, None, None

# API FETCH FUNCTIONS

def fetch_weather(lat, lon, start_date, end_date):
    try:
        url = (
            f"https://archive-api.open-meteo.com/v1/archive?"
            f"latitude={lat}&longitude={lon}"
            f"&start_date={start_date}&end_date={end_date}"
            "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
            "&timezone=auto"
        )
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"Weather API error: {e}")
        return None


def fetch_forecast(lat, lon, days=14):
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
            f"&forecast_days={days}&timezone=auto"
        )
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"Forecast API error: {e}")
        return None


def fetch_flood(lat, lon, start_date, end_date):
    try:
        url = (
            f"https://flood-api.open-meteo.com/v1/flood?"
            f"latitude={lat}&longitude={lon}"
            f"&start_date={start_date}&end_date={end_date}"
            "&daily=river_discharge&timezone=auto"
        )
        resp = requests.get(url, timeout=20)
        if resp.status_code == 404:
            return {"error": "No flood model available for this region"}
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": f"Flood API failed: {e}"}


# ANALYSIS FUNCTIONS
def analyze_extremes(df):
    events = {}
    if df is not None and not df.empty and "tmax" in df.columns and "rain" in df.columns:
        events["heatwave_days"] = int((df["tmax"] > 40).sum())
        events["drought_days"] = int((df["rain"] < 1).sum())
        events["flood_days"] = int((df["rain"] > 100).sum())
    else:
        events["heatwave_days"] = 0
        events["drought_days"] = 0
        events["flood_days"] = 0
    return events


def generate_report(region, start_date, end_date, weather_df, forecast_df, extremes, flood_data=None):
    report = []
    report.append("🌾 **Farmer Support Report**")
    report.append(f"**Region:** {region}")
    report.append(f"**Period:** {start_date} → {end_date}\n")

    if weather_df is not None and not weather_df.empty:
        report.append("📊 **Weather Summary (History):**")
        report.append(f"- Avg Temp: {weather_df['tmax'].mean():.1f} °C")
        report.append(f"- Total Rainfall: {weather_df['rain'].sum():.1f} mm\n")

    if forecast_df is not None and not forecast_df.empty:
        report.append("🔮 **Forecast (Next 14 days):**")
        report.append(f"- Expected Avg Temp: {forecast_df['tmax'].mean():.1f} °C")
        report.append(f"- Expected Rainfall: {forecast_df['rain'].sum():.1f} mm\n")

    report.append("⚠️ **Extreme Events Detected:**")
    report.append(f"- Heatwave days: {extremes.get('heatwave_days', 0)}")
    report.append(f"- Drought-like days: {extremes.get('drought_days', 0)}")
    report.append(f"- Heavy rain days: {extremes.get('flood_days', 0)}\n")

    # 🌊 Flood Risk Report
    if flood_data and "daily" in flood_data:
        try:
            discharge_vals = flood_data["daily"]["river_discharge"]
            avg_discharge = sum(discharge_vals) / len(discharge_vals)
            max_discharge = max(discharge_vals)
            report.append("🌊 **Flood Risk Report:**")
            report.append(f"- Avg River Discharge: {avg_discharge:.1f} m³/s")
            report.append(f"- Max River Discharge: {max_discharge:.1f} m³/s")
            if max_discharge > 5000:
                report.append("⚠️ High flood risk detected → Take protective measures for crops & livestock.")
            elif max_discharge > 2000:
                report.append("⚠️ Moderate flood risk → Ensure drainage systems are clear.")
            else:
                report.append("✅ No significant flood risk detected.")
            report.append("")
        except Exception:
            report.append("🌊 Flood Risk Report: Data unavailable.\n")

    if weather_df is not None and not weather_df.empty:
        if weather_df['rain'].mean() > 5 and weather_df['tmax'].mean() > 25:
            rec_crop = "Rice"
        else:
            rec_crop = "Wheat"
        report.append(f"✅ **Crop Recommendation:** Grow **{rec_crop}** this season.")

    # ✅ Safe comparisons with default=0
    if extremes.get("drought_days", 0) > 10:
        report.append("💡 Advice: Long dry spell detected → Plan irrigation.")
    if extremes.get("heatwave_days", 0) > 3:
        report.append("💡 Advice: Heat stress risk → Use heat-tolerant seeds.")
    if extremes.get("flood_days", 0) > 2:
        report.append("💡 Advice: Risk of waterlogging → Ensure drainage.")

    return "\n".join(report)


# STREAMLIT APP
st.set_page_config(page_title="Farm Analytics", layout="wide")
st.title("🌱 Farm Analytics – Prototype")
st.markdown("Weather + Forecast + Extreme Events + Interactive Visualizations + Farmer Report + Flood Analysis")

# Inputs
region = st.text_input("Enter region name:", "My Farm")

# Location selection
use_auto_loc = st.checkbox("📍 Use my current location")
if use_auto_loc:
    lat, lon, city = get_user_location()
    if lat and lon:
        st.success(f"Detected location → {city} ({lat}, {lon})")
        region = city if city else region
    else:
        st.warning("Could not detect location automatically. Please enter manually.")
        lat = st.number_input("Latitude", value=28.6139)
        lon = st.number_input("Longitude", value=77.2090)
else:
    lat = st.number_input("Latitude", value=28.6139)
    lon = st.number_input("Longitude", value=77.2090)

start_date = st.date_input("Start date", date.today() - timedelta(days=365))
end_date = st.date_input("End date", date.today())

# =====================
# RUN ANALYSIS
# =====================
if st.button("🚀 Run Full Analysis"):
    with st.spinner("Fetching data and running analysis..."):
        # Historical weather
        weather_data = fetch_weather(lat, lon, start_date, end_date)
        weather_df = None
        if weather_data:
            weather_df = pd.DataFrame({
                "date": weather_data["daily"]["time"],
                "tmax": weather_data["daily"]["temperature_2m_max"],
                "tmin": weather_data["daily"]["temperature_2m_min"],
                "rain": weather_data["daily"]["precipitation_sum"],
            })
            weather_df["date"] = pd.to_datetime(weather_df["date"])
            st.success("✅ Historical weather data fetched")

            # Temperature trend
            st.subheader("🌡️ Temperature Trend (History)")
            fig_temp = px.line(weather_df, x="date", y=["tmax", "tmin"],
                               labels={"value": "Temperature (°C)", "date": "Date"},
                               title="Daily Max & Min Temperature")
            st.plotly_chart(fig_temp, use_container_width=True)

            # Rainfall trend
            st.subheader("🌧️ Rainfall Trend (History)")
            fig_rain = px.bar(weather_df, x="date", y="rain",
                              labels={"rain": "Rainfall (mm)", "date": "Date"},
                              title="Daily Rainfall")
            st.plotly_chart(fig_rain, use_container_width=True)

            # Temperature distribution pie
            st.subheader("🌡️ Temperature Distribution (History)")
            temp_bins = pd.cut(weather_df["tmax"],
                               bins=[-5, 20, 30, 40, 50],
                               labels=["Cool (<20°C)", "Moderate (20-30°C)", "Hot (30-40°C)", "Extreme (>40°C)"])
            temp_counts = temp_bins.value_counts().reset_index()
            temp_counts.columns = ["Category", "Days"]

            fig_pie_temp = px.pie(temp_counts, values="Days", names="Category", hole=0.4,
                                  title="Temperature Category Distribution")
            st.plotly_chart(fig_pie_temp, use_container_width=True)

        # Forecast
        forecast_data = fetch_forecast(lat, lon, days=14)
        forecast_df = None
        if forecast_data:
            forecast_df = pd.DataFrame({
                "date": forecast_data["daily"]["time"],
                "tmax": forecast_data["daily"]["temperature_2m_max"],
                "tmin": forecast_data["daily"]["temperature_2m_min"],
                "rain": forecast_data["daily"]["precipitation_sum"],
            })
            forecast_df["date"] = pd.to_datetime(forecast_df["date"])
            st.success("✅ Forecast data fetched")

            fig_forecast = px.line(forecast_df, x="date", y=["tmax", "tmin"],
                                   labels={"value": "Temperature (°C)", "date": "Date"},
                                   title="Forecast: Max & Min Temperatures")
            st.plotly_chart(fig_forecast, use_container_width=True)

            fig_rain_forecast = px.bar(forecast_df, x="date", y="rain",
                                       labels={"rain": "Rainfall (mm)", "date": "Date"},
                                       title="Forecast: Daily Rainfall")
            st.plotly_chart(fig_rain_forecast, use_container_width=True)

        # Extreme events
        extremes = analyze_extremes(weather_df)
        st.subheader("⚠️ Extreme Event Analysis")
        st.write(extremes)

        # Flood model
        flood_data = fetch_flood(lat, lon, start_date, end_date)
        if "error" in flood_data:
            st.warning(f"Flood API unavailable → {flood_data['error']}")
        else:
            st.success("✅ Flood risk data fetched")

            # Flood forecast bar graph
            st.subheader("🌊 Flood Forecast – River Discharge")
            flood_df = pd.DataFrame({
                "date": flood_data["daily"]["time"],
                "river_discharge": flood_data["daily"]["river_discharge"]
            })
            flood_df["date"] = pd.to_datetime(flood_df["date"])

            fig_flood = px.bar(flood_df, x="date", y="river_discharge",
                               labels={"river_discharge": "River Discharge (m³/s)", "date": "Date"},
                               title="Flood Forecast: River Discharge Levels")
            st.plotly_chart(fig_flood, use_container_width=True)

        # Crop suitability pie
        st.subheader("🌾 Crop Suitability (Climate-based)")
        if weather_df is not None and not weather_df.empty:
            avg_temp = weather_df["tmax"].mean()
            avg_rain = weather_df["rain"].mean()

            crops = {}
            if avg_rain > 5 and avg_temp > 25:
                crops["Rice"] = 50
                crops["Maize"] = 30
                crops["Sugarcane"] = 20
            else:
                crops["Wheat"] = 60
                crops["Barley"] = 25
                crops["Pulses"] = 15

            crop_df = pd.DataFrame({"Crop": crops.keys(), "Suitability": crops.values()})
            fig_pie_crop = px.pie(crop_df, values="Suitability", names="Crop", hole=0.3,
                                  title="Crop Suitability Distribution")
            st.plotly_chart(fig_pie_crop, use_container_width=True)

        # Farmer Report
        st.subheader("📑 Farmer Report")
        report = generate_report(region, start_date, end_date, weather_df, forecast_df, extremes, flood_data)
        st.markdown(report)

