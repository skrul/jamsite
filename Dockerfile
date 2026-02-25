FROM debian:12-slim
ARG ENVIRONMENT=production
ARG SONGS_DIR=/data/songs
ARG DROPBOX_TOKEN_FILE=/secrets/dropbox_token.txt
ARG GOOGLE_API_TOKEN_PICKLE_FILE=/secrets/token.pickle

RUN apt-get update && \
    apt-get install --no-install-suggests --no-install-recommends --yes \
    python3 \
    python3-venv \
    nginx \
    python-is-python3 \
    curl

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV PATH="/root/.local/bin:${PATH}"
ENV SONGS_DIR=${SONGS_DIR}
ENV DROPBOX_TOKEN_FILE=${DROPBOX_TOKEN_FILE}
ENV GOOGLE_API_TOKEN_PICKLE_FILE=${GOOGLE_API_TOKEN_PICKLE_FILE}
ENV GOOGLE_API_CREDENTIALS_FILE=${GOOGLE_API_CREDENTIALS_FILE}

WORKDIR /src
COPY pyproject.toml uv.lock .
COPY jamsite/ jamsite/
RUN uv sync --no-dev --frozen

COPY ./nginx/nginx.conf /etc/nginx/nginx.conf
COPY ./nginx/${ENVIRONMENT}.conf /etc/nginx/conf.d/server.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 80
EXPOSE 443

ENTRYPOINT ["/entrypoint.sh"]
