FROM debian:12-slim

RUN apt-get update && \
    apt-get install --no-install-suggests --no-install-recommends --yes \
    python3 \
    pipx \
    nginx \
    python-is-python3

ENV PATH="/root/.local/bin:${PATH}"
RUN pipx install poetry
RUN pipx inject poetry poetry-plugin-bundle

WORKDIR /src
COPY pyproject.toml poetry.lock .
COPY jamsite/ jamsite/
RUN poetry bundle venv --python=/usr/bin/python3 --only=main /venv

RUN --mount=type=secret,id=google_api_token_pickle \
  GOOGLE_API_TOKEN_PICKLE_FILE=/run/secrets/google_api_token_pickle \
  /venv/bin/jamsite --generate
# FROM debian:12-slim
# COPY --from=builder /venv /venv

COPY ./nginx/nginx.conf /etc/nginx/nginx.conf
COPY ./jamsite/dist/jam /usr/share/nginx/html

EXPOSE 80

ENTRYPOINT ["nginx", "-g", "daemon off;"]
#ENTRYPOINT ["sleep", "infinity"]
#ENTRYPOINT ["/venv/bin/my-awesome-app"]
