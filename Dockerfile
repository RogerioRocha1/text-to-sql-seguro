FROM python:3.12-slim

ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Dependências numa camada própria, lidas do pyproject.toml: mudar o código em
# src/ não reinstala Streamlit, pandas etc. (a parte demorada do build).
COPY pyproject.toml ./
RUN python -c "import tomllib; print('\n'.join(tomllib.load(open('pyproject.toml', 'rb'))['project']['dependencies']))" > /tmp/requisitos.txt \
    && pip install -r /tmp/requisitos.txt

COPY src ./src
RUN pip install --no-deps .

RUN useradd --create-home app
USER app

# A interface (serviço app) usa a 8501; sem comando, a imagem roda a carga.
EXPOSE 8501
CMD ["python", "-m", "assistente_sql.carga"]
