# The game server's two services (compose.yaml), built on the machine from
# the files the Deploy workflow sends: jk2mvded comes built (on GitHub, for
# the machine's architecture), so the machine compiles nothing.

# --- The dedicated server, with the site's pack and server.cfg mounted at
# /od/base; logs and the server's own settings go to /od/home
FROM ubuntu:24.04 AS jk2mvded
LABEL opendojo=1

RUN useradd --system --home-dir /od od && mkdir -p /od/home && chown od /od/home
COPY jk2mvded /usr/local/bin/jk2mvded
USER od

ENTRYPOINT ["jk2mvded", "+set", "fs_basepath", "/od", "+set", "fs_homepath", "/od/home", "+set", "net_port", "28170"]
CMD ["+set", "dedicated", "1", "+exec", "server.cfg"]

# --- The relay (relay.mjs), on 127.0.0.1 only: Caddy is in front of it
FROM node:22-bookworm-slim AS relay
LABEL opendojo=1

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev
COPY relay.mjs ./
USER node

CMD ["node", "relay.mjs", "--port", "8081", "--game", "127.0.0.1:28170"]
