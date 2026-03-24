FROM python:3.12-slim

# Peruspaketit (build, git, jne.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Asenna uv (Python-riippuvuudet)
RUN pip install --no-cache-dir uv

WORKDIR /app

# Kopioi projektin metatiedot (uv osaa näistä asentaa kirjastot)
COPY pyproject.toml uv.lock ./

# Asenna riippuvuudet (ml. dbt-core ja dbt-duckdb, kun ne on pyprojectissa)
RUN uv sync --frozen

# Kopioi koko projekti konttiin
COPY . .

# Varmistetaan, että dbt löytää profiilin (mountataan hostin ~/.dbt compose-tiedostossa)
ENV DBT_PROFILES_DIR=/root/.dbt

# Oletuskomento: avatkaa säiliö shelliin ja ajakaa dbt käsin
CMD ["/bin/bash"]
