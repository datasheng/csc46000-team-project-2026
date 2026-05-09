# Tableau Dashboard Guide

Connect Tableau Desktop to MySQL and use the tables created by the final notebook section, **Tableau Dashboard Tables**.

## MySQL Tables

| Dashboard | Table | Purpose |
| --- | --- | --- |
| Live Traffic Predictions | `tableau_today_weather_predictions` | Forecast-style borough predictions using current or template weather inputs |
| Live Traffic Predictions | `tableau_live_predictions_by_borough` | Borough-level predicted delay probability, delay index, and hotspot fields |
| City Weather Comparison | `tableau_weather_delay_summary` | Rain, temperature, season, borough, and delay-risk summaries |
| A/B Model Results | `tableau_model_results` | Classification and regression model metrics |
| Detail Drilldown | `tableau_ml_predictions_detail` | Row-level rush-hour prediction detail |

## Dashboard 1: Live Traffic Predictions

Use `tableau_today_weather_predictions` for the live forecast view.

Recommended worksheets:

1. **Prediction Map**
   - Columns: `longitude`
   - Rows: `latitude`
   - Marks: Circle or Map
   - Detail: `boro`
   - Color: `predicted_delay_probability`
   - Size: `predicted_delay_probability`
   - Tooltip: `boro`, `hour`, `temperature_2m`, `precipitation`, `congestion_level`

2. **Predicted Delay by Borough**
   - Columns: `boro`
   - Rows: `predicted_delay_probability`
   - Color: `congestion_level`
   - Sort descending by `predicted_delay_probability`

3. **Congestion KPI Tiles**
   - Highest predicted borough
   - Average predicted delay probability
   - Number of severe boroughs
   - Forecast hour

Suggested calculated field:

```tableau
Severe Borough Flag =
IF [congestion_level] = "Severe" THEN 1 ELSE 0 END
```

## Dashboard 2: City Weather Comparison

Use `tableau_weather_delay_summary`.

Recommended worksheets:

1. **Rain vs Delay by Borough**
   - Columns: `boro`
   - Rows: `delay_risk_rate`
   - Color: `rain_intensity`

2. **Seasonal Delay Trend**
   - Columns: `season`
   - Rows: `avg_delay_index`
   - Color: `boro`

3. **Weather Heatmap**
   - Columns: `rain_intensity`
   - Rows: `temp_bin`
   - Color: `delay_risk_rate`
   - Label: `delay_risk_rate`
   - Filter: `boro`, `season`

4. **Weather Impact Table**
   - Rows: `boro`, `season`
   - Measures: `avg_temperature`, `avg_precipitation`, `delay_risk_rate`, `avg_delay_index`

## Dashboard 3: A/B Model Results

Use `tableau_model_results`.

Recommended worksheets:

1. **Classification Model Comparison**
   - Filter: `model_type = classification`
   - Columns: `model`
   - Rows: `accuracy`, `precision`, `recall`, `f1`, `roc_auc`

2. **Regression Model Comparison**
   - Filter: `model_type = regression`
   - Columns: `model`
   - Rows: `rmse`, `r2`

3. **Best Model Recommendation**
   - Text: `model`
   - Filter: `recommendation = Recommended`
   - Tooltip: `selection_score`, `model_type`

4. **Metric Tiles**
   - Best ROC-AUC
   - Best F1
   - Lowest RMSE
   - Highest R2

Suggested calculated field:

```tableau
Best Fit Label =
IF [recommendation] = "Recommended" THEN "Best Fit" ELSE "Compare" END
```

## Refresh Flow

Run the notebook in this order:

1. API ingestion cells
2. MySQL connection cell
3. ML pipeline cells
4. Tableau Dashboard Tables cell
5. Refresh Tableau

The intended flow is:

```text
Weather/traffic APIs -> Python ML pipeline -> MySQL Tableau tables -> Tableau dashboards
```

