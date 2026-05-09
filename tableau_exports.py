import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


BOROUGH_CENTROIDS = pd.DataFrame(
    {
        "boro": ["Bronx", "Brooklyn", "Manhattan", "Queens", "Staten Island"],
        "latitude": [40.8448, 40.6782, 40.7831, 40.7282, 40.5795],
        "longitude": [-73.8648, -73.9442, -73.9712, -73.7949, -74.1502],
    }
)


def _clean_model_inputs(df, weather_features):
    cleaned = df.copy()
    categorical_cols = [
        col
        for col in weather_features
        if col not in ["hour", "temperature_2m", "precipitation"]
    ]
    for col in categorical_cols:
        cleaned[col] = cleaned[col].astype("object").where(cleaned[col].notna(), "missing").astype(str)
    return cleaned


def _build_regression_model(feature_cols, model):
    numeric_features = [
        col for col in feature_cols if col in ["hour", "temperature_2m", "precipitation"]
    ]
    categorical_features = [col for col in feature_cols if col not in numeric_features]

    preprocessor = ColumnTransformer(
        [
            (
                "num",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric_features,
            ),
            (
                "cat",
                Pipeline([("encoder", OneHotEncoder(handle_unknown="ignore"))]),
                categorical_features,
            ),
        ]
    )

    return Pipeline([("preprocessor", preprocessor), ("model", model)])


def build_tableau_tables(rush_df, rush_scored, model_results, weather_features, weather_model):
    """Create Tableau-ready DataFrames from the notebook ML outputs."""
    rush_df = _clean_model_inputs(rush_df, weather_features)
    rush_scored = _clean_model_inputs(rush_scored, weather_features)

    x_train, x_test, y_train, y_test = train_test_split(
        rush_df[weather_features],
        rush_df["delay_index"],
        test_size=0.25,
        random_state=42,
    )

    regression_models = {
        "model_a_linear_regression": _build_regression_model(
            weather_features, LinearRegression()
        ),
        "model_b_random_forest": _build_regression_model(
            weather_features,
            RandomForestRegressor(
                n_estimators=300,
                min_samples_leaf=3,
                random_state=42,
            ),
        ),
    }

    regression_rows = []
    for name, model in regression_models.items():
        model.fit(x_train[weather_features], y_train)
        predictions = model.predict(x_test[weather_features])
        regression_rows.append(
            {
                "model": name,
                "model_type": "regression",
                "rmse": mean_squared_error(y_test, predictions) ** 0.5,
                "r2": r2_score(y_test, predictions),
            }
        )

    regression_results = pd.DataFrame(regression_rows)

    classification_results = model_results.copy()
    classification_results["model_type"] = "classification"
    classification_results["rmse"] = None
    classification_results["r2"] = None

    regression_results["accuracy"] = None
    regression_results["precision"] = None
    regression_results["recall"] = None
    regression_results["f1"] = None
    regression_results["roc_auc"] = None

    tableau_model_results = pd.concat(
        [classification_results, regression_results],
        ignore_index=True,
        sort=False,
    )

    tableau_model_results["selection_score"] = tableau_model_results.apply(
        lambda row: row["roc_auc"] if pd.notna(row.get("roc_auc")) else row.get("r2", -999),
        axis=1,
    )
    best_model = (
        tableau_model_results.sort_values("selection_score", ascending=False)
        .iloc[0]["model"]
    )
    tableau_model_results["recommendation"] = tableau_model_results["model"].apply(
        lambda model: "Recommended" if model == best_model else "Compare"
    )

    predictions_by_borough = (
        rush_scored.groupby("boro")
        .agg(
            avg_predicted_delay_probability=("predicted_delay_probability", "mean"),
            avg_delay_index=("delay_index", "mean"),
            delay_risk_rate=("delay_risk", "mean"),
            avg_temperature=("temperature_2m", "mean"),
            avg_precipitation=("precipitation", "mean"),
            records=("delay_risk", "size"),
        )
        .reset_index()
        .merge(BOROUGH_CENTROIDS, on="boro", how="left")
    )
    predictions_by_borough["congestion_level"] = pd.cut(
        predictions_by_borough["avg_predicted_delay_probability"],
        bins=[-0.001, 0.10, 0.20, 0.35, 1.0],
        labels=["Low", "Moderate", "High", "Severe"],
    ).astype(str)

    weather_detail = rush_scored.copy()
    weather_detail["season"] = weather_detail["date"].dt.month.map(
        {
            12: "Winter",
            1: "Winter",
            2: "Winter",
            3: "Spring",
            4: "Spring",
            5: "Spring",
            6: "Summer",
            7: "Summer",
            8: "Summer",
            9: "Fall",
            10: "Fall",
            11: "Fall",
        }
    )

    weather_summary = (
        weather_detail.groupby(["boro", "season", "rain_intensity", "temp_bin"], observed=True)
        .agg(
            avg_delay_index=("delay_index", "mean"),
            delay_risk_rate=("delay_risk", "mean"),
            avg_predicted_delay_probability=("predicted_delay_probability", "mean"),
            avg_temperature=("temperature_2m", "mean"),
            avg_precipitation=("precipitation", "mean"),
            records=("delay_risk", "size"),
        )
        .reset_index()
    )

    today_weather_predictions = _build_today_weather_predictions(
        rush_df, weather_features, weather_model
    )

    return {
        "tableau_ml_predictions_detail": rush_scored,
        "tableau_live_predictions_by_borough": predictions_by_borough,
        "tableau_weather_delay_summary": weather_summary,
        "tableau_model_results": tableau_model_results,
        "tableau_today_weather_predictions": today_weather_predictions,
    }


def _build_today_weather_predictions(rush_df, weather_features, weather_model):
    today = pd.Timestamp.today()
    template = pd.DataFrame(
        {
            "boro": BOROUGH_CENTROIDS["boro"],
            "street": [rush_df["street"].mode().iloc[0]] * len(BOROUGH_CENTROIDS),
            "direction": [rush_df["direction"].mode().iloc[0]] * len(BOROUGH_CENTROIDS),
            "day_of_week": [today.day_name()] * len(BOROUGH_CENTROIDS),
            "hour": [8] * len(BOROUGH_CENTROIDS),
            "temperature_2m": [rush_df["temperature_2m"].median()] * len(BOROUGH_CENTROIDS),
            "precipitation": [rush_df["precipitation"].median()] * len(BOROUGH_CENTROIDS),
        }
    )
    template["is_raining"] = template["precipitation"] > 0
    template["rain_intensity"] = pd.cut(
        template["precipitation"],
        bins=[-0.001, 0, 0.05, 0.15, float("inf")],
        labels=["none", "light", "moderate", "heavy"],
    ).astype(str)
    template["temp_bin"] = pd.cut(
        template["temperature_2m"],
        bins=[-float("inf"), 32, 45, 60, 75, float("inf")],
        labels=["freezing", "cold", "mild", "warm", "hot"],
    ).astype(str)
    template = _clean_model_inputs(template, weather_features)
    template["predicted_delay_probability"] = weather_model.predict_proba(
        template[weather_features]
    )[:, 1]
    template = template.merge(BOROUGH_CENTROIDS, on="boro", how="left")
    template["congestion_level"] = pd.cut(
        template["predicted_delay_probability"],
        bins=[-0.001, 0.10, 0.20, 0.35, 1.0],
        labels=["Low", "Moderate", "High", "Severe"],
    ).astype(str)
    return template


def write_tableau_tables(engine, tables):
    """Write Tableau-ready tables to MySQL."""
    for table_name, dataframe in tables.items():
        dataframe.to_sql(table_name, con=engine, if_exists="replace", index=False)
    return list(tables.keys())
