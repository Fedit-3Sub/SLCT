FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt ./
COPY main.py /app

RUN pip install -r requirements.txt

EXPOSE 9901
CMD ["python", "main.py"]
