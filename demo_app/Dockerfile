FROM python:3.9-slim@sha256:2d97f6910b16bd338d3060f261f53f144965f755599aab1acda1e13cf1731b1b

WORKDIR /app

COPY constraints.txt /app/constraints.txt
COPY demo_app/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -c /app/constraints.txt -r /app/requirements.txt

COPY demo_app /app/demo_app/

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "demo_app.main:app", "--host", "0.0.0.0", "--port", "8000"]
