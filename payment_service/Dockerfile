# Sử dụng Python 3.9 slim làm base image
FROM python:3.9-slim

# Thiết lập thư mục làm việc trong container
WORKDIR /app

# Copy file requirements.txt vào container trước
COPY requirements.txt .

# Cài đặt các thư viện cần thiết
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ code của service vào container
COPY . .

# Lệnh chạy app (sẽ được ghi đè trong docker-compose nhưng cứ để đây cho chuẩn)
# Lưu ý: Lệnh này giả định file chạy là main.py
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]