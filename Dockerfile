FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/decision/requirements.txt
RUN python -m pip install --no-cache-dir \
    -r /tmp/decision/requirements.txt

COPY .devops/packages/port_strategy_common-1.0.0-*.whl /tmp/packages/
RUN COMMON_WHEEL="$(find /tmp/packages -maxdepth 1 -type f -name 'port_strategy_common-1.0.0-*.whl' | head -n 1)" \
    && test -n "${COMMON_WHEEL}" \
    && python -m pip install --no-cache-dir --no-deps "${COMMON_WHEEL}" \
    && rm -rf /tmp/packages

COPY . /app/port_strategy_decision

CMD ["python", "-m", "port_strategy_decision.daily_buy_signal_run"]