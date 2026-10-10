#!/bin/sh
# Deploys Open Dojo's game server from a tar on stdin, sent by the Deploy
# workflow over SSH: compose.yaml, Dockerfile, the built jk2mvded, the relay
# with package.json and package-lock.json, and base/ with the site's
# opendojo.pk3 and server.cfg. Installed on the machine as
# /usr/local/bin/opendojo-deploy, the only command its key can run (see
# "Deploying" in README.md); a new version only takes effect when it's
# installed there again.
#
# Everything stays in /srv/opendojo and the compose project opendojo: it
# never touches anything else on the machine. It rebuilds the services when
# what they're built from changed, and restarts the game server when the
# pack or server.cfg changed (the pack changes on every build: the page and
# the server must have the same one).
set -eu
app=/srv/opendojo
new=$(mktemp -d)
trap 'rm -rf "$new"' EXIT

tar -x -C "$new"
test -f "$new/compose.yaml" && test -f "$new/base/opendojo.pk3" ||
	{ echo "deploy: not an Open Dojo server" >&2; exit 1; }

# a hash of some of the server's files
inputs() {
	(cd "$app" && find "$@" -type f 2>/dev/null | LC_ALL=C sort | xargs -r sha256sum | sha256sum)
}
images="compose.yaml Dockerfile jk2mvded relay.mjs package.json package-lock.json"
# shellcheck disable=SC2086
images_before=$(inputs $images)
base_before=$(inputs base)

rsync -a --delete "$new"/ "$app"/

cd "$app"
# shellcheck disable=SC2086
if [ -z "$(docker compose ps -q)" ] || [ "$(inputs $images)" != "$images_before" ]; then
	echo "deploy: rebuilding"
	docker compose up -d --build --remove-orphans
	docker image prune -f --filter label=opendojo=1 > /dev/null
fi
if [ "$(inputs base)" != "$base_before" ]; then
	echo "deploy: the pack or server.cfg changed, restarting the game server"
	docker compose restart jk2mvded
fi
docker compose ps --format '{{.Service}}: {{.Status}}'
