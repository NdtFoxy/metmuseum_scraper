FROM python:3.9-slim-buster

WORKDIR /app

COPY "Main v4.py" .

RUN pip install requests beautifulsoup4 lxml urllib3

CMD ["python", "Main v4.py"]