FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .

RUN useradd --create-home app
USER app

CMD ["python", "-m", "assistente_sql.carga"]
