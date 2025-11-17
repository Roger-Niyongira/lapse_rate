import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# Page config
st.set_page_config(page_title="Lapse Curves", layout="wide")

# Title
st.title("Lapse Rate Curve Plotter")

# Plot by and Chart type selector
col1, col2 = st.columns(2)

with col1:
    chart_type = st.radio(
        "**CHART TYPE**",
        ["Scatter + trendline", "Line"],
        horizontal=False
    )

with col2:
    plot_by = st.radio(
        "**PLOT BY**",
        ["Timeseries", "Altitude", "Mean annual"],
        horizontal=False,
    )

# SIDE BAR
uploaded = st.sidebar.file_uploader(
    "**Upload CSV File**",
    type=["csv", "xlsx"]
)

if uploaded is None:
    st.info("Please upload the provided CSV file")
    st.stop()

df = pd.read_csv(uploaded)

DATE_COL = "date"

df[DATE_COL] = pd.to_datetime(df[DATE_COL])
selected_gauges = []
selected_years = []
all_chart_paths = []

gauge_list = df["Gauge"].unique()
years_list = df["Year"].unique()

st.sidebar.header("SELECT STATION")

# for ALTITUDE modes → all selected by default
if plot_by in ["Altitude", "Mean annual"]:
    default_selected = True
    key_prefix = "alt_gauge_"   # different keys so defaults work
else:
    default_selected = False
    key_prefix = "gauge_"

for gauge in gauge_list:
    checked = st.sidebar.checkbox(
        str(gauge),
        key=f"{key_prefix}{gauge}",
        value=default_selected,
    )
    if checked:
        selected_gauges.append(gauge)

st.sidebar.header("SELECT YEAR")
for year in years_list:
    if pd.isna(year):
        continue
    if st.sidebar.checkbox(str(year), key=f"year_{year}"):
        selected_years.append(year)

y_min = df["Temp_lapse"].min() - 1
y_max = df["Temp_lapse"].max() + 1

# MAIN CONTENT
if not selected_gauges:
    st.info("No gauges selected")
elif not selected_years:
    st.info("No years selected")
else:
    for yr in selected_years:
        df_year = df[df["Year"] == yr]

        # ALTITUDE selected: all gauges are choses unless otherwise
        if plot_by == "Altitude":
            df_alt = df_year[df_year["Gauge"].isin(selected_gauges)].copy()

            if df_alt.empty:
                st.info(f"No data available for selected gauges in {yr}")
                continue

            st.subheader(f"Temperature vs elevation – {yr}")

            chart = (
                alt.Chart(df_alt)
                .mark_point()
                .encode(
                    x=alt.X("Elevation_m", title="Elevation (m)"),
                    y=alt.Y("TEMP_AVE",
                            title="Temperature (°C)"),
                    color=alt.Color("Gauge", title="Gauge"),
                    tooltip=["Gauge", "Elevation_m", "TEMP_AVE", DATE_COL]
                )
            )

            st.altair_chart(chart, use_container_width=True)
            continue  # next year

        if plot_by == "Mean annual":
            df_ma = df_year[df_year["Gauge"].isin(selected_gauges)]

            if df_ma.empty:
                st.info(f"No data for selected gauges in {yr}")
                continue

            df_ma_agg = (
                df_ma.groupby(["Gauge", "Elevation_m"], as_index=False)["TEMP_AVE"]
                .mean()
            )

            st.subheader(f"Mean Temperature rate vs elevation – {yr}")

            chart = (
                alt.Chart(df_ma_agg)
                .mark_point(size=120)
                .encode(
                    x=alt.X("Elevation_m", title="Elevation (m)"),
                    y=alt.Y("TEMP_AVE", title="Mean annual temp (°C)"),
                    color="Gauge",
                    tooltip=["Gauge", "Elevation_m", "TEMP_AVE"]
                )
            )

            st.altair_chart(chart, use_container_width=True)
            continue

        # TIMESERIES per selected station
        cols = [None, None]
        for i, gauge in enumerate(selected_gauges):
            df_plot = (
                df_year[df_year["Gauge"] == gauge]
                .sort_values(DATE_COL)
            )

            if i % 2 == 0:
                cols = st.columns(2)

            with cols[i % 2]:
                st.markdown(f"**{gauge} - {yr}**")

                if plot_by == "Timeseries":
                    base = alt.Chart(df_plot).encode(
                        x=alt.X(
                            DATE_COL,
                            title="Date",
                            type="temporal",
                            axis=alt.Axis(format="%Y-%m-%d")
                        ),
                        y=alt.Y(
                            "Temp_lapse",
                            title="Lapse Rate (°C/km)",
                            scale=alt.Scale(domain=[y_min, y_max])
                        )
                    )

                    if chart_type == "Line":
                        chart = base.mark_line()
                    else:
                        points = base.mark_point()
                        trend = base.transform_regression(
                            DATE_COL, "Temp_lapse"
                        ).mark_line()
                        chart = points + trend

                        x_num = (df_plot[DATE_COL] - df_plot[DATE_COL].min()).dt.days.astype(float)
                        y = df_plot["Temp_lapse"].astype(float).values

                        if len(x_num) > 1:
                            m, b = np.polyfit(x_num, y, 1)
                            y_pred = m * x_num + b
                            ss_res = np.sum((y - y_pred) ** 2)
                            ss_tot = np.sum((y - y.mean()) ** 2)
                            r2 = 1 - ss_res / ss_tot if ss_tot != 0 else np.nan

                            st.caption(
                                f"Trendline: {m:.3f}·day + {b:.3f}  (°C/km),  R² = {r2:.3f}"
                            )

                    st.altair_chart(chart, use_container_width=True)

