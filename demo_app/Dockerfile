FROM python:3.11-slim@sha256:0dd364ba7e10242f07755449e3a3d0e35f9efd987952737b90def6709ab0c5ce

WORKDIR /app

COPY constraints.txt /app/constraints.txt
COPY demo_app/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -c /app/constraints.txt -r /app/requirements.txt

COPY demo_app /app/demo_app/

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "demo_app.main:app", "--host", "0.0.0.0", "--port", "8000"]
