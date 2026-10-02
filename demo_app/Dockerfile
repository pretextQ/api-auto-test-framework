FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app/demo_app/

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "demo_app.main:app", "--host", "0.0.0.0", "--port", "8000"]
