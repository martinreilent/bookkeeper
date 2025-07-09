FROM python:slim AS builder

RUN apt-get update && apt-get install -y git python3-dev build-essential \
    && rm -rf /var/lib/apt/lists/* # Clean up apt cache

RUN pip install --root-user-action ignore --prefix="/install" fava git+https://github.com/andreasgerstmayr/fava-dashboards.git

FROM python:slim

COPY --from=builder /install /usr/local

ENV FAVA_HOST="0.0.0.0"
EXPOSE 5000
CMD ["fava"]