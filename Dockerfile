FROM python:3.9-slim-buster

WORKDIR /app

COPY Main_v4.py .

RUN pip install requests beautifulsoup4 lxml urllib3
RUN pip install pysocks

CMD ["python", "Main_v4.py"]
