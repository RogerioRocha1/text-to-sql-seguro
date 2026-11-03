FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .

RUN useradd --create-home app
USER app

# A interface (serviço app) usa a 8501; sem comando, a imagem roda a carga.
EXPOSE 8501
CMD ["python", "-m", "assistente_sql.carga"]
