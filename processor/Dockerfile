FROM python:3.10-slim-buster

WORKDIR /app

COPY requirements.txt ./
COPY main.py /app
COPY .env .env

RUN pip install -r requirements.txt

EXPOSE 9901
CMD ["python", "main.py"]
