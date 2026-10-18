IoT Data Collection, Storage and Preprocessing

Học phần: IoT và Ứng dụng (INT14149)
Sinh viên: Doãn Dình Hải
Mã sinh viên: B23DCCN269

1. Giới thiệu

Dự án xây dựng hệ thống thu thập, lưu trữ và tiền xử lý dữ liệu IoT từ ESP32 mô phỏng trên Wokwi.

Hệ thống sử dụng ThingsBoard để tiếp nhận telemetry, Python để thu thập dữ liệu, InfluxDB Cloud 2.x để lưu trữ dữ liệu chuỗi thời gian và Python/Pandas để tiền xử lý.

Kiến trúc hệ thống
ESP32 (Wokwi)
    |
    | MQTT telemetry
    v
ThingsBoard Cloud
    |
    | REST API
    v
mqtt_to_influx.py
    |
    | Raw data
    v
InfluxDB Cloud
    |
    | Query raw data
    v
preprocessing.py
    |
    | Cleaned and processed data
    v
InfluxDB Cloud

2. Công nghệ sử dụng
Python 3
ESP32 và cảm biến DHT22, HC-SR04
ThingsBoard Cloud
InfluxDB Cloud 2.x
paho-mqtt
requests
influxdb-client
pandas
numpy
python-dotenv
3. Cấu trúc thư mục
IoT/
├── .venv/
├── .env
├── .gitignore
├── mqtt_to_influx.py
├── preprocessing.py
└── README.md

4. Yêu cầu trước khi chạy
4.1. Cài đặt Python

Cài Python tương thích với các thư viện trong dự án. Khuyến nghị Python 3.10 hoặc mới hơn.

Kiểm tra phiên bản:

python --version

4.2. Tạo môi trường ảo

Mở PowerShell tại thư mục dự án:

cd C:\Users\Admin\Desktop\IoT

python -m venv .venv

.\.venv\Scripts\Activate.ps1


Nếu PowerShell chặn việc kích hoạt môi trường ảo, có thể chạy:

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1

4.3. Cài đặt thư viện
python -m pip install --upgrade pip

pip install requests influxdb-client pandas numpy python-dotenv paho-mqtt

4.4. Chuẩn bị InfluxDB Cloud

Trong InfluxDB Cloud, cần chuẩn bị:

Organization: Ptit
Raw bucket: iot_data
Processed bucket: iot_processed
API Token có quyền ghi vào bucket dữ liệu xử lý và quyền đọc dữ liệu thô.

Nếu chưa có bucket, hãy tạo hai bucket trên giao diện InfluxDB Cloud.

Lưu ý: Tên Organization và bucket phải khớp chính xác với cấu hình thực tế.

4.5. Chuẩn bị ThingsBoard
ESP32 phải gửi telemetry thành công lên ThingsBoard.
Lấy Device ID của thiết bị ESP32.
Chuẩn bị API Key có quyền đọc telemetry nếu phiên bản ThingsBoard đang dùng hỗ trợ loại xác thực này.

Device Access Token dùng để thiết bị gửi MQTT không mặc nhiên là REST API Key.

5. Cấu hình biến môi trường

Tạo file .env tại thư mục gốc của dự án:

# ThingsBoard
TB_HOST=https://thingsboard.cloud
TB_API_KEY=YOUR_THINGSBOARD_API_KEY
TB_DEVICE_ID=YOUR_DEVICE_UUID

# InfluxDB Cloud
INFLUX_URL=https://YOUR_INFLUXDB_HOST
INFLUX_TOKEN=YOUR_INFLUXDB_TOKEN
INFLUX_ORG=Ptit

# Buckets
RAW_BUCKET=iot_data
PROCESSED_BUCKET=iot_processed

# Raw data configuration
DEVICE_ID=ESP32_BAI2
LOOKBACK=-24h

# Preprocessing
PREPROCESS_CONTINUOUS=false
PREPROCESS_INTERVAL=60


Thay các giá trị mẫu bằng thông tin thật.

TB_API_KEY: API Key được ThingsBoard hỗ trợ cho REST API.
TB_DEVICE_ID: UUID của thiết bị trên ThingsBoard.
INFLUX_URL: URL của InfluxDB Cloud.
INFLUX_TOKEN: token truy cập InfluxDB.
INFLUX_ORG: Organization thực tế.
DEVICE_ID: tag device_id có trong dữ liệu thô.

Không chia sẻ file .env công khai hoặc tải file này lên GitHub.

Kiểm tra tên measurement

Trong preprocessing.py, mặc định:

RAW_MEASUREMENT = "sensor_data"
PROCESSED_MEASUREMENT = "sensor_processed"


Tên measurement của dữ liệu thô phải khớp với mqtt_to_influx.py. Nếu Collector ghi vào sensor_raw, hãy sửa RAW_MEASUREMENT thành sensor_raw.

6. Chạy chương trình thu thập dữ liệu
Bước 1: Khởi chạy ESP32

Mở mô phỏng Wokwi và chạy chương trình ESP32.

Kiểm tra Serial Monitor để xác nhận thiết bị gửi telemetry thành công.

Bước 2: Chạy Collector

Mở Terminal tại thư mục dự án và kích hoạt .venv:

.\.venv\Scripts\Activate.ps1
python mqtt_to_influx.py


Nếu cấu hình đúng, chương trình sẽ kết nối ThingsBoard, đọc telemetry và ghi dữ liệu vào InfluxDB.

Kiểm tra dữ liệu trong InfluxDB Cloud bằng Data Explorer.

Nếu không có dữ liệu, kiểm tra:

API Key và quyền truy cập thiết bị.
Device ID.
URL và token InfluxDB.
Tên bucket và measurement.
Các trường telemetry: temperature, humidity, distance_cm.

Lưu ý: Collector sử dụng REST API polling nên cần API Key tương thích với ThingsBoard. Nếu ThingsBoard không hỗ trợ loại API Key đó, cần đổi phương thức xác thực trước khi chạy Collector.

7. Chạy chương trình tiền xử lý

Sau khi dữ liệu thô đã được lưu vào InfluxDB, mở một Terminal khác hoặc dừng Collector bằng Ctrl+C.

Chạy:

python preprocessing.py


Chương trình thực hiện:

Đọc dữ liệu thô trong khoảng thời gian cấu hình.
Chuyển timestamp sang UTC và loại bản ghi trùng timestamp.
Resample dữ liệu thành các cửa sổ một phút.
Nội suy các khoảng thiếu ngắn.
Phát hiện outlier bằng phương pháp IQR.
Tính trung bình trượt nhiệt độ trên ba mẫu.
Chuẩn hóa nhiệt độ, độ ẩm và khoảng cách về khoảng [0, 1].
Ghi kết quả vào measurement sensor_processed.

Kết quả được lưu vào bucket iot_processed.

Chạy tiền xử lý định kỳ

Để tự động xử lý mỗi 60 giây, cập nhật file .env:

PREPROCESS_CONTINUOUS=true
PREPROCESS_INTERVAL=60


Sau đó chạy lại:

python preprocessing.py


Dừng bằng Ctrl+C.

Lưu ý: Chế độ định kỳ hiện tại xử lý lại cửa sổ dữ liệu đã cấu hình. Khi triển khai lâu dài, nên bổ sung checkpoint hoặc chỉ xử lý dữ liệu mới để tránh tính toán lặp.

8. Kiểm tra dữ liệu trong InfluxDB

Trong InfluxDB Cloud:

Mở Data Explorer.
Chọn bucket iot_data để kiểm tra dữ liệu thô.
Chọn bucket iot_processed để kiểm tra dữ liệu đã xử lý.
Chọn khoảng thời gian phù hợp, ví dụ Last 24 hours.

Các trường trong sensor_processed:

Field	Ý nghĩa
temperature	Nhiệt độ sau tiền xử lý
humidity	Độ ẩm sau tiền xử lý
distance_cm	Khoảng cách sau tiền xử lý
temp_rolling_mean	Trung bình trượt nhiệt độ ba mẫu
temp_scaled	Nhiệt độ chuẩn hóa Min-Max
hum_scaled	Độ ẩm chuẩn hóa Min-Max
dist_scaled	Khoảng cách chuẩn hóa Min-Max
9. Xử lý lỗi thường gặp
Lỗi KeyError khi đọc biến môi trường

Nguyên nhân: thiếu biến trong .env hoặc file không được tải.

Khắc phục:

Đảm bảo .env nằm cùng thư mục với file Python.
Gọi load_dotenv() trước khi đọc biến môi trường.
Kiểm tra tên biến và khởi chạy từ thư mục dự án.
Lỗi 401 Unauthorized

Nguyên nhân: token không hợp lệ hoặc không có quyền truy cập.

Khắc phục:

Kiểm tra API Key ThingsBoard.
Kiểm tra InfluxDB token.
Đảm bảo không nhầm Device Access Token với REST API Key.
Lỗi 404 Organization not found

Nguyên nhân: tên Organization không khớp.

Khắc phục:

Kiểm tra Organization trong giao diện InfluxDB.
Cập nhật INFLUX_ORG trong .env.
Không tìm thấy dữ liệu thô

Nguyên nhân:

ESP32 chưa gửi telemetry.
Collector chưa ghi thành công.
Tên measurement, bucket hoặc device_id bị sai.
Khoảng thời gian truy vấn không chứa dữ liệu.

Khắc phục: kiểm tra dữ liệu trong Data Explorer và đối chiếu cấu hình trong preprocessing.py.

Lỗi ghi dữ liệu do NaN

Nguyên nhân: dữ liệu thiếu hoặc không hợp lệ.

Khắc phục: bỏ qua các giá trị NaN và vô cực trước khi tạo Point().

10. Lưu ý về độ chính xác dữ liệu
Nội suy chỉ nên áp dụng cho khoảng thiếu ngắn.
IQR có thể loại nhầm biến động thực tế của cảm biến.
Min-Max Scaling trên từng batch có thể khiến giá trị chuẩn hóa thay đổi khi dữ liệu mới xuất hiện.
Dữ liệu được resample mỗi phút nên không còn thể hiện đầy đủ biến động ở chu kỳ năm giây.
Cần phân biệt thời gian đo, thời gian nhận dữ liệu và thời gian ghi database khi đánh giá độ trễ end-to-end.
11. Thứ tự chạy toàn hệ thống
Chạy mô phỏng ESP32 trên Wokwi.
Kiểm tra telemetry trên ThingsBoard.
Chạy mqtt_to_influx.py để thu thập và lưu dữ liệu thô.
Chạy preprocessing.py để xử lý dữ liệu.
Ki
