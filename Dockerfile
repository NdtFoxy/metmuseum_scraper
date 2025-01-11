FROM python:3.9-slim-buster

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все необходимые файлы в контейнер
COPY Main_v4.py config.yaml ./

# Указываем команду по умолчанию, если не будет переопределено в docker-compose
CMD ["python", "Main_v4.py", "run"]
