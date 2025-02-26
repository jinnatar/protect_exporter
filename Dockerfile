FROM ghcr.io/astral-sh/uv:0.6.2-python3.13-alpine AS builder
RUN mkdir /build
WORKDIR /build

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv build

FROM python:3.13-alpine
WORKDIR /srv
COPY --from=builder /build/dist/*.whl ./
RUN pip install *.whl && rm *.whl

ENTRYPOINT ["protect_exporter"]
