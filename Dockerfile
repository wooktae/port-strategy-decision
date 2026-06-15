FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY port_strategy_decision/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Temporary vendoring for AWS smoke.
# Formal port_strategy_common packaging/versioning is deferred to strategy-common hardening.
COPY port_strategy_common /app/port_strategy_common
COPY port_strategy_decision /app/port_strategy_decision

CMD ["python", "-m", "port_strategy_decision.daily_buy_signal_run"]
