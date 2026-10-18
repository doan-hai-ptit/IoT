
# README - HE THONG IOT

## 1. Gioi thieu

Du an thu thap, luu tru va tien xu ly du lieu IoT tu ESP32 mo phong tren Wokwi.

He thong su dung ThingsBoard de tiep nhan telemetry va InfluxDB Cloud 2.x de luu tru du lieu.

Hai chuong trinh chinh:

- mqtt_to_influx.py: Thu thap du lieu va ghi vao InfluxDB.
- preprocessing.py: Doc du lieu tho, lam sach, chuan hoa va ghi du lieu da xu ly.

## 2. Cau truc thu muc

```text
IoT/
|-- .venv/
|-- .env
|-- mqtt_to_influx.py
|-- preprocessing.py
|-- README.md
|-- .gitignore
```

## 3. Cai dat moi truong

Mo PowerShell tai thu muc du an:

```powershell
cd C:\Users\Admin\Desktop\IoT
```

Tao moi truong ao:

```powershell
python -m venv .venv
```

Kich hoat moi truong ao:

```powershell
.\.venv\Scripts\Activate.ps1
```

Cai dat cac thu vien:

```powershell
python -m pip install --upgrade pip
pip install requests influxdb-client pandas numpy python-dotenv paho-mqtt
```

## 4. Cau hinh file .env

Tao file co ten chinh xac la `.env` trong thu muc du an.

Noi dung:

```dotenv
TB_HOST=https://thingsboard.cloud
TB_API_KEY=YOUR_THINGSBOARD_API_KEY
TB_DEVICE_ID=YOUR_DEVICE_UUID

INFLUX_URL=https://YOUR_INFLUXDB_HOST
INFLUX_TOKEN=YOUR_INFLUXDB_TOKEN
INFLUX_ORG=Ptit

RAW_BUCKET=iot_data
PROCESSED_BUCKET=iot_processed

DEVICE_ID=ESP32_BAI2

LOOKBACK=-24h
PREPROCESS_CONTINUOUS=false
PREPROCESS_INTERVAL=60
```

Thay cac gia tri mau bang thong tin thuc te.

Luu y:
- INFLUX_ORG phai dung ten Organization tren InfluxDB.
- RAW_BUCKET la bucket chua du lieu tho.
- PROCESSED_BUCKET la bucket chua du lieu da xu ly.
- TB_DEVICE_ID la UUID cua thiet bi tren ThingsBoard.
- DEVICE_ID phai khop voi tag device_id trong du lieu tho.
- API Key ThingsBoard phai duoc ho tro boi phien ban dang su dung va co quyen doc telemetry.

## 5. Chay chuong trinh thu thap du lieu

### Buoc 1: Khoi dong ESP32

Mo mo phong ESP32 tren Wokwi va nhan Start.

Kiem tra Serial Monitor de dam bao ESP32 gui telemetry len ThingsBoard thanh cong.

### Buoc 2: Chay mqtt_to_influx.py

Trong PowerShell:

```powershell
python mqtt_to_influx.py
```

Chuong trinh se doc telemetry tu ThingsBoard va ghi du lieu tho vao InfluxDB.

Kiem tra du lieu trong InfluxDB Cloud bang Data Explorer.

## 6. Chay chuong trinh tien xu ly

Sau khi du lieu tho da duoc ghi vao InfluxDB, mo Terminal va chay:

```powershell
python preprocessing.py
```

Chuong trinh thuc hien:

1. Doc du lieu tho tu InfluxDB.
2. Xu ly gia tri thieu bang noi suy.
3. Phat hien va xu ly outlier bang phuong phap IQR.
4. Resample du lieu theo cua so 1 phut.
5. Tao dac trung temp_rolling_mean voi cua so 3 mau.
6. Chuan hoa Min-Max ve khoang [0, 1].
7. Ghi du lieu da xu ly vao measurement sensor_processed.

### Chay tien xu ly lien tuc

Sua file `.env`:

```dotenv
PREPROCESS_CONTINUOUS=true
PREPROCESS_INTERVAL=60
```

Chay lai:

```powershell
python preprocessing.py
```

Nhan Ctrl+C de dung chuong trinh.

## 7. Schema du lieu

### 7.1. Du lieu tho

- Bucket: iot_data
- Measurement: sensor_data
- Tag: device_id
- Fields:
  - temperature
  - humidity
  - distance_cm
  - rssi
  - sequence

Luu y: Neu mqtt_to_influx.py dang ghi vao measurement sensor_raw, can sua RAW_MEASUREMENT trong preprocessing.py thanh sensor_raw.

### 7.2. Du lieu da xu ly

- Bucket: iot_processed
- Measurement: sensor_processed
- Tag: device_id
- Fields:
  - temperature
  - humidity
  - distance_cm
  - temp_rolling_mean
  - temp_scaled
  - hum_scaled
  - dist_scaled

## 8. Kiem tra tren InfluxDB

1. Dang nhap InfluxDB Cloud.
2. Mo Data Explorer.
3. Chon bucket iot_data de xem du lieu tho.
4. Chon bucket iot_processed de xem du lieu da xu ly.
5. Chon khoang thoi gian Last 24 hours.

## 9. Xu ly loi thuong gap

### Loi KeyError

Kiem tra file `.env`, ten bien moi truong va lenh load_dotenv().

### Loi 401 Unauthorized

Kiem tra API Key ThingsBoard hoac INFLUX_TOKEN.

### Loi 404 Organization Not Found

Kiem tra INFLUX_ORG co dung ten Organization hay khong.

### Loi Bucket Not Found

Kiem tra RAW_BUCKET va PROCESSED_BUCKET da ton tai tren InfluxDB hay chua.

### Khong co du lieu

Kiem tra:
- ESP32 da gui telemetry thanh cong.
- mqtt_to_influx.py da ghi du lieu vao InfluxDB.
- Ten measurement va device_id chinh xac.
- LOOKBACK bao gom khoang thoi gian co du lieu.

### Loi NaN khi ghi du lieu

Loai bo gia tri NaN va vo cuc truoc khi tao Point().

## 10. Danh gia he thong

ESP32 gui du lieu moi 5 giay. Neu hoat dong lien tuc, mot thiet bi tao khoang 17.280 ban ghi moi ngay.

Tien xu ly giup:
- Xu ly gia tri thieu.
- Phat hien gia tri bat thuong.
- Lam min chuoi thoi gian.
- Chuan hoa du lieu.
- Tao dac trung phuc vu phan tich.

## 11. Bao mat

Tao file `.gitignore`:

```gitignore
.venv/
.env
__pycache__/
*.pyc
```

Khong cong khai API Key, InfluxDB Token hoac mat khau tren GitHub.

## 12. Thu tu chay he thong

1. Khoi dong ESP32 tren Wokwi.
2. Kiem tra telemetry tren ThingsBoard.
3. Chay mqtt_to_influx.py.
4. Kiem tra du lieu tho trong InfluxDB.
5. Chay preprocessing.py.
6. Kiem tra measurement sensor_processed.
7. Chay dashboard neu co.

Ket qua mong doi: Du lieu tu ESP32 duoc thu thap, luu tru trong InfluxDB Cloud, tien xu ly va san sang cho viec truc quan hoa.
