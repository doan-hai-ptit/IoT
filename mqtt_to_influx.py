
import os
import time
import math
import requests

from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# ==========================================
# 1. LOAD CONFIGURATION
# ==========================================
load_dotenv()

TB_HOST = os.getenv(
    "TB_HOST", "https://thingsboard.cloud"
).rstrip("/")

TB_API_KEY = os.environ["TB_API_KEY"]
TB_DEVICE_ID = os.environ["TB_DEVICE_ID"]

INFLUX_URL = os.environ["INFLUX_URL"]
INFLUX_TOKEN = os.environ["INFLUX_TOKEN"]
INFLUX_ORG = os.environ["INFLUX_ORG"]
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "iot_data")

POLL_INTERVAL = 5

# ==========================================
# 2. HTTP SESSION
# ==========================================
session = requests.Session()

# API Key authentication (not Device Access Token)
session.headers.update({
    "X-Authorization": f"ApiKey {TB_API_KEY}",
    "Accept": "application/json",
})

# ==========================================
# 3. INFLUXDB
# ==========================================
db = InfluxDBClient(
    url=INFLUX_URL,
    token=INFLUX_TOKEN,
    org=INFLUX_ORG,
)

write_api = db.write_api(
    write_options=SYNCHRONOUS
)

# Remember the last processed telemetry timestamp
last_timestamp = 0

# ==========================================
# 4. READ TELEMETRY FROM THINGSBOARD
# ==========================================
def get_latest_telemetry():
    url = (
        f"{TB_HOST}/api/plugins/telemetry/DEVICE/"
        f"{TB_DEVICE_ID}/values/timeseries"
    )

    params = {
        "keys": (
            "temperature,humidity,distance_cm,"
            "rssi,sequence,uptime_s"
        ),
        "limit": 1,
    }

    response = session.get(
        url,
        params=params,
        timeout=15,
    )

    if response.status_code == 401:
        raise RuntimeError(
            "401 Unauthorized: API Key khong hop le "
            "hoac khong du quyen."
        )

    if response.status_code == 403:
        raise RuntimeError(
            "403 Forbidden: API Key khong co quyen "
            "doc telemetry cua thiet bi."
        )

    if response.status_code == 404:
        raise RuntimeError(
            "404 Not Found: Kiem tra TB_HOST va TB_DEVICE_ID."
        )

    response.raise_for_status()
    return response.json()


# ==========================================
# 5. EXTRACT TELEMETRY
# ==========================================
def extract_latest(data):
    result = {}

    for key, items in data.items():
        if items:
            # Each telemetry item contains ts and value
            result[key] = items[0]

    return result


def numeric_value(telemetry, key):
    item = telemetry.get(key)

    if item is None:
        return None

    try:
        value = float(item["value"])

        if not math.isfinite(value):
            return None

        return value

    except (ValueError, TypeError, KeyError):
        return None


# ==========================================
# 6. WRITE TELEMETRY TO INFLUXDB
# ==========================================
def save_to_influx(data):
    global last_timestamp

    telemetry = extract_latest(data)

    if not telemetry:
        print("Chua co telemetry tren ThingsBoard.")
        return

    # Use the latest measurement timestamp as record time
    timestamps = [
        int(item["ts"])
        for item in telemetry.values()
        if "ts" in item
    ]

    if not timestamps:
        print("Telemetry khong co timestamp.")
        return

    timestamp_ms = max(timestamps)

    if timestamp_ms <= last_timestamp:
        print("Chua co ban tin moi.")
        return

    temperature = numeric_value(telemetry, "temperature")
    humidity = numeric_value(telemetry, "humidity")
    distance = numeric_value(telemetry, "distance_cm")

    if None in (temperature, humidity, distance):
        print(
            "Thieu du lieu: can temperature, humidity, "
            "distance_cm."
        )
        print("Keys nhan duoc:", list(telemetry.keys()))
        return

    point = (
        Point("sensor_raw")
        .tag("device_id", TB_DEVICE_ID)
        .tag("location", "lab")
        .field("temperature", temperature)
        .field("humidity", humidity)
        .field("distance_cm", distance)
        .time(timestamp_ms * 1_000_000, WritePrecision.NS)
    )

    rssi = numeric_value(telemetry, "rssi")
    sequence = numeric_value(telemetry, "sequence")
    uptime = numeric_value(telemetry, "uptime_s")

    if rssi is not None:
        point = point.field("rssi", int(rssi))

    if sequence is not None:
        point = point.field("sequence", int(sequence))

    if uptime is not None:
        point = point.field("uptime_s", int(uptime))

    write_api.write(
        bucket=INFLUX_BUCKET,
        org=INFLUX_ORG,
        record=point,
    )

    last_timestamp = timestamp_ms

    print(
        f"[SAVED] {time.strftime('%H:%M:%S')} | "
        f"temperature={temperature:.2f} C | "
        f"humidity={humidity:.2f}% | "
        f"distance={distance:.2f} cm"
    )


# ==========================================
# 7. MAIN LOOP
# ==========================================
def main():
    print("=" * 50)
    print("THINGSBOARD -> INFLUXDB")
    print("=" * 50)
    print("ThingsBoard:", TB_HOST)
    print("Device ID:", TB_DEVICE_ID)
    print("InfluxDB:", INFLUX_URL)
    print("Bucket:", INFLUX_BUCKET)

    # Verify API Key access before polling
    print("\nTesting ThingsBoard API Key...")

    data = get_latest_telemetry()
    print("API request successful.")
    print("Telemetry keys:", list(data.keys()))

    print("\nStarting telemetry polling...")
    print("Press Ctrl+C to stop.\n")

    while True:
        try:
            data = get_latest_telemetry()
            save_to_influx(data)

        except requests.RequestException as exc:
            print("[HTTP ERROR]", exc)

        except RuntimeError as exc:
            print("[AUTH ERROR]", exc)

        except Exception as exc:
            print("[ERROR]", repr(exc))

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    try:
        main()

    except KeyboardInterrupt:
        print("\nStopped.")

    except Exception as exc:
        print("[FATAL]", repr(exc))

    finally:
        write_api.close()
        db.close()
        session.close()
