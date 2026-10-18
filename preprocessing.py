
import os
import time
import logging

import numpy as np
import pandas as pd

from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# ==================================================
# 1. CONFIGURATION
# ==================================================
load_dotenv()

INFLUX_URL = os.environ["INFLUX_URL"]
INFLUX_TOKEN = os.environ["INFLUX_TOKEN"]
INFLUX_ORG = os.getenv("INFLUX_ORG", "Ptit")

# Raw data and processed data buckets
RAW_BUCKET = os.getenv("RAW_BUCKET", "iot_data")
PROCESSED_BUCKET = os.getenv(
    "PROCESSED_BUCKET", "iot_processed"
)

RAW_MEASUREMENT = "sensor_data"
PROCESSED_MEASUREMENT = "sensor_processed"

DEVICE_ID = os.getenv("DEVICE_ID", "ESP32_BAI2")

# Query the latest 24 hours
LOOKBACK = os.getenv("LOOKBACK", "-24h")

# Run once, or continuously if enabled
RUN_INTERVAL_SECONDS = int(
    os.getenv("PREPROCESS_INTERVAL", "60")
)

CONTINUOUS = os.getenv(
    "PREPROCESS_CONTINUOUS", "false"
).lower() == "true"

RESAMPLE_WINDOW = "1min"
ROLLING_WINDOW = 3

METRICS = [
    "temperature",
    "humidity",
    "distance_cm",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

# ==================================================
# 2. INFLUXDB CLIENT
# ==================================================
client = InfluxDBClient(
    url=INFLUX_URL,
    token=INFLUX_TOKEN,
    org=INFLUX_ORG,
)

query_api = client.query_api()
write_api = client.write_api(
    write_options=SYNCHRONOUS
)


# ==================================================
# 3. READ RAW DATA
# ==================================================
def read_raw_data():
    query = f'''
    from(bucket: "{RAW_BUCKET}")
      |> range(start: {LOOKBACK})
      |> filter(fn: (r) =>
          r["_measurement"] == "{RAW_MEASUREMENT}"
      )
      |> filter(fn: (r) =>
          r["_field"] == "temperature" or
          r["_field"] == "humidity" or
          r["_field"] == "distance_cm"
      )
      |> filter(fn: (r) =>
          r["device_id"] == "{DEVICE_ID}"
      )
      |> pivot(
          rowKey: ["_time"],
          columnKey: ["_field"],
          valueColumn: "_value"
      )
      |> keep(columns: [
          "_time",
          "device_id",
          "temperature",
          "humidity",
          "distance_cm"
      ])
      |> sort(columns: ["_time"])
    '''

    result = query_api.query_data_frame(
        query=query,
        org=INFLUX_ORG,
    )

    if isinstance(result, list):
        frames = [
            frame for frame in result
            if not frame.empty
        ]
        if not frames:
            return pd.DataFrame()
        df = pd.concat(frames, ignore_index=True)
    else:
        df = result

    if df.empty:
        return df

    df["_time"] = pd.to_datetime(
        df["_time"], utc=True, errors="coerce"
    )

    for col in METRICS:
        if col not in df.columns:
            df[col] = np.nan

        df[col] = pd.to_numeric(
            df[col], errors="coerce"
        )

    df = df.dropna(subset=["_time"])
    df = df.sort_values("_time")

    # Remove duplicated timestamps before resampling
    df = df.drop_duplicates(
        subset=["_time"], keep="last"
    )

    logging.info("Raw records loaded: %d", len(df))
    return df


# ==================================================
# 4. MISSING VALUES
# ==================================================
def handle_missing_values(df):
    df = df.copy()

    df = df.set_index("_time").sort_index()

    # Create a regular 1-minute time series
    df = df[METRICS].resample(
        RESAMPLE_WINDOW
    ).mean()

    # Interpolate only short internal gaps.
    # Do not fill leading/trailing missing values.
    df[METRICS] = df[METRICS].interpolate(
        method="time",
        limit=2,
        limit_area="inside",
    )

    return df


# ==================================================
# 5. OUTLIER DETECTION USING IQR
# ==================================================
def remove_outliers_iqr(df):
    df = df.copy()

    for col in METRICS:
        valid = df[col].dropna()

        if len(valid) < 4:
            logging.warning(
                "Not enough values for IQR: %s", col
            )
            continue

        q1 = valid.quantile(0.25)
        q3 = valid.quantile(0.75)
        iqr = q3 - q1

        if not np.isfinite(iqr) or iqr == 0:
            continue

        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr

        outlier_mask = (
            (df[col] < lower) |
            (df[col] > upper)
        )

        count = int(outlier_mask.sum())

        if count:
            logging.info(
                "%s: detected %d outliers",
                col, count
            )

        # Mark outliers as missing, then interpolate
        df.loc[outlier_mask, col] = np.nan

        df[col] = df[col].interpolate(
            method="time",
            limit=2,
            limit_area="inside",
        )

    return df


# ==================================================
# 6. FEATURE ENGINEERING AND MIN-MAX SCALING
# ==================================================
def create_features(df):
    df = df.copy()

    # Rolling mean of 3 one-minute samples
    df["temp_rolling_mean"] = (
        df["temperature"].rolling(
            window=ROLLING_WINDOW,
            min_periods=1,
        ).mean()
    )

    # Min-Max scaling to [0, 1]
    # Use the valid values in this processing batch.
    for source, target in [
        ("temperature", "temp_scaled"),
        ("humidity", "hum_scaled"),
        ("distance_cm", "dist_scaled"),
    ]:
        valid = df[source].dropna()

        if valid.empty:
            df[target] = np.nan
            continue

        minimum = valid.min()
        maximum = valid.max()
        value_range = maximum - minimum

        if value_range == 0:
            df[target] = np.where(
                df[source].notna(), 0.0, np.nan
            )
        else:
            df[target] = (
                (df[source] - minimum) / value_range
            )

    return df


# ==================================================
# 7. WRITE PROCESSED DATA
# ==================================================
def write_processed_data(df):
    if df.empty:
        logging.warning("No processed data to write")
        return

    fields = [
        "temperature",
        "humidity",
        "distance_cm",
        "temp_rolling_mean",
        "temp_scaled",
        "hum_scaled",
        "dist_scaled",
    ]

    written = 0

    for timestamp, row in df.iterrows():
        point = (
            Point(PROCESSED_MEASUREMENT)
            .tag("device_id", DEVICE_ID)
        )

        valid_fields = 0

        for field in fields:
            value = row.get(field, np.nan)

            if pd.isna(value):
                continue

            value = float(value)

            if not np.isfinite(value):
                continue

            point = point.field(field, value)
            valid_fields += 1

        # Never write an empty point
        if valid_fields == 0:
            continue

        point = point.time(
            timestamp.to_pydatetime(),
            WritePrecision.NS,
        )

        write_api.write(
            bucket=PROCESSED_BUCKET,
            org=INFLUX_ORG,
            record=point,
        )

        written += 1

    logging.info(
        "Processed records written: %d", written
    )


# ==================================================
# 8. PREPROCESSING PIPELINE
# ==================================================
def process_data():
    logging.info("Starting preprocessing")

    raw = read_raw_data()

    if raw.empty:
        logging.warning(
            "No raw data found. Check bucket, "
            "measurement and device_id."
        )
        return

    df = handle_missing_values(raw)

    df = remove_outliers_iqr(df)

    df = create_features(df)

    # Drop rows that have no usable sensor values
    df = df.dropna(subset=METRICS, how="all")

    if df.empty:
        logging.warning(
            "No valid rows remain after preprocessing"
        )
        return

    write_processed_data(df)

    logging.info(
        "Preprocessing completed: %d rows", len(df)
    )


# ==================================================
# 9. MAIN
# ==================================================
if __name__ == "__main__":
    try:
        while True:
            try:
                process_data()
            except Exception:
                logging.exception(
                    "Preprocessing pipeline failed"
                )

            if not CONTINUOUS:
                break

            time.sleep(RUN_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        logging.info("Stopped by user")

    finally:
        write_api.close()
        client.close()
