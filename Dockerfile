FROM python:3.11-slim@sha256:0dd364ba7e10242f07755449e3a3d0e35f9efd987952737b90def6709ab0c5ce

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt constraints.txt ./
COPY demo_app/requirements.txt ./demo-requirements.txt
RUN pip install --no-cache-dir -c constraints.txt \
    -r requirements.txt -r demo-requirements.txt

COPY . .

RUN mkdir -p reports/allure logs

ENV PYTHONPATH=/app
ENV TEST_ENV=test

CMD ["pytest", "-m", "unit or smoke"]
