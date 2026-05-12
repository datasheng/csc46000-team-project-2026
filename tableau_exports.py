import pandas as pd


BOROUGH_CENTROIDS = pd.DataFrame(
    {
        "boro": ["Bronx", "Brooklyn", "Manhattan", "Queens", "Staten Island"],
        "latitude": [40.8448, 40.6782, 40.7831, 40.7282, 40.5795],
        "longitude": [-73.8648, -73.9442, -73.9712, -73.7949, -74.1502],
    }
)

NUMERIC_FEATURES = ["vol", "hour", "temperature_2m", "precipitation"]


def _clean_model_inputs(df, feature_cols):
    cleaned = df.copy()
    categorical_cols = [
        col
        for col in feature_cols
        if col not in NUMERIC_FEATURES
    ]
    for col in categorical_cols:
        if col in cleaned.columns:
            cleaned[col] = (
                cleaned[col]
                .astype("object")
                .where(cleaned[col].notna(), "missing")
                .astype(str)
            )
    return cleaned


def _delay_level(series):
    return pd.cut(
        series,
        bins=[-0.001, 5, 15, 30, float("inf")],
        labels=["Low", "Moderate", "High", "Severe"],
    ).astype(str)


def build_tableau_tables(
    rush_df,
    rush_scored,
    model_results,
    weather_features,
    weather_model,
    city_df=None,
):
    """Create Tableau-ready tables for the three required dashboards."""
    rush_df = _clean_model_inputs(rush_df, weather_features)
    rush_scored = _clean_model_inputs(rush_scored, weather_features)
    city_source = rush_scored if city_df is None else city_df.copy()

    detail_cols = [
        "date",
        "hour",
        "boro",
        "street",
        "fromst",
        "tost",
        "direction",
        "vol",
        "expected_volume",
        "p75_volume",
        "p90_volume",
        "volume_ratio",
        "volume_delta",
        "congestion_score",
        "is_moderate_congestion",
        "is_volume_spike",
        "weather_pressure",
        "delay_score",
        "delay_index",
        "delay_minutes",
        "predicted_delay_minutes",
        "delay_level",
        "rain_intensity",
        "temperature_2m",
        "precipitation",
        "is_raining",
        "day_of_week",
    ]
    detail_cols = [col for col in detail_cols if col in rush_scored.columns]
    live_predictions = rush_scored[detail_cols].copy()
    live_predictions["prediction_error_minutes"] = (
        live_predictions["delay_minutes"]
        - live_predictions["predicted_delay_minutes"]
    )
    live_predictions["is_raining_flag"] = (
        live_predictions["is_raining"].astype(str).str.lower().eq("true")
    )
    live_predictions["table_scope"] = "rush_hour_scored_records"

    live_by_borough = (
        live_predictions.groupby("boro", as_index=False)
        .agg(
            records=("delay_minutes", "size"),
            avg_actual_delay_minutes=("delay_minutes", "mean"),
            avg_predicted_delay_minutes=("predicted_delay_minutes", "mean"),
            avg_precipitation=("precipitation", "mean"),
            rainy_record_share=("is_raining_flag", "mean"),
        )
        .merge(BOROUGH_CENTROIDS, on="boro", how="left")
    )
    live_by_borough["delay_level"] = _delay_level(
        live_by_borough["avg_predicted_delay_minutes"]
    )

    city_source = _prepare_city_comparison_source(
        city_source,
        weather_features,
        weather_model,
    )
    city_comparison = (
        city_source.groupby(["boro", "rain_intensity"], observed=True)
        .agg(
            records=("delay_minutes", "size"),
            avg_delay_minutes=("delay_minutes", "mean"),
            avg_predicted_delay_minutes=("predicted_delay_minutes", "mean"),
            avg_delay_index=("delay_index", "mean"),
            avg_temperature=("temperature_2m", "mean"),
            avg_precipitation=("precipitation", "mean"),
            total_precipitation=("precipitation", "sum"),
            max_precipitation=("precipitation", "max"),
        )
        .reset_index()
        .merge(BOROUGH_CENTROIDS, on="boro", how="left")
    )
    city_comparison["table_scope"] = "all_city_records"
    city_comparison["delay_level"] = _delay_level(
        city_comparison["avg_predicted_delay_minutes"]
    )

    ab_results = model_results.copy()
    ab_results["dashboard"] = "A/B results"
    if "rmse" in ab_results.columns:
        ab_results["recommendation_score"] = -ab_results["rmse"]
        best_model = ab_results.sort_values("rmse", ascending=True).iloc[0]["model"]
        ab_results["recommendation"] = ab_results["model"].apply(
            lambda model: "Recommended" if model == best_model else "Compare"
        )

    today_weather_predictions = _build_today_weather_predictions(
        rush_df,
        weather_features,
        weather_model,
    )

    return {
        "tableau_live_predictions": live_predictions,
        "tableau_live_predictions_by_borough": live_by_borough,
        "tableau_city_comparison": city_comparison,
        "tableau_ab_results": ab_results,
        "tableau_today_weather_predictions": today_weather_predictions,
    }


def _prepare_city_comparison_source(city_source, weather_features, weather_model):
    city_source = city_source.copy()
    if "rain_intensity" not in city_source.columns:
        city_source["rain_intensity"] = pd.cut(
            city_source["precipitation"],
            bins=[-0.001, 0, 0.05, 0.15, float("inf")],
            labels=["none", "light", "moderate", "heavy"],
        )
    city_source = _clean_model_inputs(city_source, weather_features)
    if "predicted_delay_minutes" not in city_source.columns:
        city_source["predicted_delay_minutes"] = weather_model.predict(
            city_source[weather_features]
        ).clip(min=0)
    return city_source


def _build_today_weather_predictions(rush_df, weather_features, weather_model):
    today = pd.Timestamp.today()
    template = (
        rush_df.groupby("boro", as_index=False)
        .agg(
            street=("street", lambda values: values.mode().iloc[0]),
            direction=("direction", lambda values: values.mode().iloc[0]),
            vol=("vol", "median"),
            temperature_2m=("temperature_2m", "median"),
            precipitation=("precipitation", "median"),
        )
        .merge(BOROUGH_CENTROIDS[["boro"]], on="boro", how="right")
    )
    template["street"] = template["street"].fillna(rush_df["street"].mode().iloc[0])
    template["direction"] = template["direction"].fillna(
        rush_df["direction"].mode().iloc[0]
    )
    template["vol"] = template["vol"].fillna(rush_df["vol"].median())
    template["temperature_2m"] = template["temperature_2m"].fillna(
        rush_df["temperature_2m"].median()
    )
    template["precipitation"] = template["precipitation"].fillna(
        rush_df["precipitation"].median()
    )
    template["day_of_week"] = today.day_name()
    template["hour"] = 8
    template["is_raining"] = template["precipitation"] > 0
    template["rain_intensity"] = pd.cut(
        template["precipitation"],
        bins=[-0.001, 0, 0.05, 0.15, float("inf")],
        labels=["none", "light", "moderate", "heavy"],
    ).astype(str)
    template = _clean_model_inputs(template, weather_features)
    template["predicted_delay_minutes"] = weather_model.predict(
        template[weather_features]
    ).clip(min=0)
    template["delay_level"] = _delay_level(template["predicted_delay_minutes"])
    template = template.merge(BOROUGH_CENTROIDS, on="boro", how="left")
    template["prediction_source"] = "borough_median_template_inputs"
    return template


def write_tableau_tables(engine, tables):
    """Write Tableau-ready tables to MySQL."""
    for table_name, dataframe in tables.items():
        dataframe.to_sql(table_name, con=engine, if_exists="replace", index=False)
    return list(tables.keys())
