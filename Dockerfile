ARG SUPERSET_VERSION=4.1.1
FROM apache/superset:${SUPERSET_VERSION}

USER root

RUN apt-get update && apt-get install -y \
        pkg-config \
        default-libmysqlclient-dev \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN if [ -x /app/.venv/bin/python ]; then \
        uv pip install --python /app/.venv/bin/python --no-cache \
            psycopg2-binary \
            redis \
            'clickhouse-connect==0.13.0' \
            mysqlclient; \
    else \
        pip install --no-cache-dir \
            psycopg2-binary \
            redis \
            'clickhouse-connect==0.13.0' \
            mysqlclient; \
    fi

USER superset
