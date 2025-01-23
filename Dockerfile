FROM debian:12-slim
ARG ENVIRONMENT=production
ARG SONGS_DIR=/data/songs
ARG DROPBOX_TOKEN_FILE=/secrets/dropbox_token.txt
ARG GOOGLE_API_TOKEN_PICKLE_FILE=/secrets/token.pickle

RUN apt-get update && \
    apt-get install --no-install-suggests --no-install-recommends --yes \
    python3 \
    pipx \
    nginx \
    python-is-python3

ENV PATH="/root/.local/bin:${PATH}"
ENV SONGS_DIR=${SONGS_DIR}
ENV DROPBOX_TOKEN_FILE=${DROPBOX_TOKEN_FILE}
ENV GOOGLE_API_TOKEN_PICKLE_FILE=${GOOGLE_API_TOKEN_PICKLE_FILE}

RUN pipx install poetry
RUN pipx inject poetry poetry-plugin-bundle

WORKDIR /src
COPY pyproject.toml poetry.lock .
COPY jamsite/ jamsite/
RUN poetry bundle venv --python=/usr/bin/python3 --only=main /venv

RUN --mount=type=secret,id=google_api_token_pickle \
  GOOGLE_API_TOKEN_PICKLE_FILE=/run/secrets/google_api_token_pickle \
  /venv/bin/jamsite --generate

# COPY webpack.config.js package.json package-lock.json .
# COPY src/ src/
# RUN npm install
# RUN npx webpack

  # FROM debian:12-slim
# COPY --from=builder /venv /venv

COPY ./nginx/nginx.conf /etc/nginx/nginx.conf
COPY ./nginx/${ENVIRONMENT}.conf /etc/nginx/conf.d/server.conf
RUN cp -r ./dist/* /usr/share/nginx/html

EXPOSE 80
EXPOSE 443

ENTRYPOINT ["nginx", "-g", "daemon off;"]
#ENTRYPOINT ["sleep", "infinity"]
#ENTRYPOINT ["/venv/bin/my-awesome-app"]
