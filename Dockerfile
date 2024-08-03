FROM python:3.11 AS poetry_builder
ENV POETRY_HOME="/opt/poetry"
ENV PATH="$POETRY_HOME/bin:$PATH"
RUN curl -sSL https://install.python-poetry.org | python -

FROM poetry_builder as builder
RUN mkdir /build
WORKDIR /build
COPY protect_exporter ./protect_exporter
COPY poetry.lock pyproject.toml ./
RUN poetry build -f wheel

FROM python:3.13.0b4-slim
WORKDIR /srv
COPY --from=builder /build/dist/*.whl ./
RUN pip install *.whl

ENTRYPOINT ["protect_exporter"]
