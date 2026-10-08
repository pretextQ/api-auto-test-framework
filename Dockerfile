FROM python:3.9-slim@sha256:2d97f6910b16bd338d3060f261f53f144965f755599aab1acda1e13cf1731b1b

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
