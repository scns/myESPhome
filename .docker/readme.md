# Docker development environments

Run each compose file from its directory, or use `docker compose -f <path> up -d`
from the repository root. Relative volume paths are resolved against the compose
file's directory.

## Website preview

The legacy `LAMP` directory now contains a small static HTTP server. It needs no
PHP, database, root password or phpMyAdmin:

```sh
docker compose -f .docker/LAMP/compose.yml up -d
```

Open http://localhost:8080. The source website has no compiled firmware, so the
installer reports unavailable firmware in this preview. Use publication artifacts
for an end-to-end installation check. The preview port is bound to localhost.

## ESPHome

`ESPhomeStable` is pinned to the version in `requirements-dev.txt`. `ESPhomeBeta`
uses the beta channel and is intended for exploratory compatibility testing.
Both mount the repository's `esphome/` directory. Avoid simultaneous edits or
builds against the same configuration in stable and beta.

Copy the adjacent `.env.example` to `.env` and replace the example dashboard
password before starting. `.env`, personal device configurations and generated
files are ignored by Git.

From the repository root, pass that env file explicitly:

```sh
docker compose --env-file .docker/ESPhomeStable/.env -f .docker/ESPhomeStable/compose.yml up -d
```

The stable container uses host networking for Linux discovery. The beta dashboard
is exposed only at http://localhost:6053. Host networking, USB passthrough and mDNS
behave differently on Docker Desktop; use the local Python CLI for USB flashing
on Windows if the container cannot access your board.

## Home Assistant

The stable dashboard uses port 8123; beta uses port 8124 so they do not conflict.
Each has its own ignored `config/` volume. The bridge network does not automatically
provide host mDNS discovery; configure the appropriate network for your host or
connect to ESPHome devices by address. These are optional development environments.
