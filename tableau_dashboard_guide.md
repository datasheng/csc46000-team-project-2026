# Tableau Dashboard Guide

Connect Tableau Desktop to MySQL and use the tables created by the final notebook section, **Tableau Dashboard Tables**.

## MySQL Tables

| Dashboard | Table | Purpose |
| --- | --- | --- |
| Live Predictions | `tableau_today_weather_predictions` | Forecast-style borough delay-minute predictions using template/current weather inputs |
| Live Predictions | `tableau_live_predictions` | Row-level rush-hour actual vs predicted delay minutes |
| Live Predictions | `tableau_live_predictions_by_borough` | Borough-level predicted delay minutes, rainy share, coordinates, and delay level |
| City Comparison | `tableau_city_comparison` | Borough and rain-intensity comparison for precipitation, delay minutes, and traffic pattern shifts |
| A/B Results | `tableau_ab_results` | Model A baseline vs Model B precipitation-aware regression metrics |

## Dashboard 1: Live Predictions

Use `tableau_today_weather_predictions` and `tableau_live_predictions_by_borough`.

Recommended worksheets:

1. **Prediction Map**
   - Columns: `longitude`
   - Rows: `latitude`
   - Marks: Circle or Map
   - Detail: `boro`
   - Color: `predicted_delay_minutes`
   - Size: `predicted_delay_minutes`
   - Tooltip: `boro`, `hour`, `temperature_2m`, `precipitation`, `delay_level`

2. **Predicted Delay by Borough**
   - Columns: `boro`
   - Rows: `avg_predicted_delay_minutes`
   - Color: `delay_level`
   - Sort descending by `avg_predicted_delay_minutes`

3. **Live KPI Tiles**
   - Highest predicted delay borough
   - Average predicted delay minutes
   - Rainy record share
   - Forecast hour

Suggested calculated field:

```tableau
Severe Delay Flag =
IF [delay_level] = "Severe" THEN 1 ELSE 0 END
```

## Dashboard 2: City Comparison

Use `tableau_city_comparison`.

Recommended worksheets:

1. **Rain Intensity by Borough**
   - Columns: `rain_intensity`
   - Rows: `boro`
   - Color: `records` or `total_precipitation`
   - Label: `records`
   - Tooltip: `avg_precipitation`, `max_precipitation`, `total_precipitation`

2. **Predicted Delay Heatmap**
   - Columns: `rain_intensity`
   - Rows: `boro`
   - Color: `avg_predicted_delay_minutes`
   - Label: `avg_predicted_delay_minutes`

3. **Weather Impact Scatter**
   - Columns: `avg_precipitation`
   - Rows: `avg_delay_minutes`
   - Color: `boro`
   - Size: `records`

4. **Comparison Table**
   - Rows: `boro`, `rain_intensity`
   - Measures: `records`, `avg_precipitation`, `total_precipitation`, `max_precipitation`, `avg_temperature`, `avg_delay_minutes`, `avg_predicted_delay_minutes`

## Dashboard 3: A/B Results

Use `tableau_ab_results`.

Recommended worksheets:

1. **Model Error Comparison**
   - Columns: `ab_group`
   - Rows: `mae`, `rmse`
   - Lower values are better

2. **Model Fit Comparison**
   - Columns: `ab_group`
   - Rows: `r2`
   - Higher values are better

3. **Best Model Recommendation**
   - Text: `model`
   - Filter: `recommendation = Recommended`
   - Tooltip: `mae`, `rmse`, `r2`

4. **Metric Tiles**
   - Lowest MAE
   - Lowest RMSE
   - Highest R2
   - Recommended model

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
Weather/traffic APIs -> precipitation-delay regression -> MySQL Tableau tables -> Tableau dashboards
```
