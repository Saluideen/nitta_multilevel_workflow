# Update Application
yes|docker builder prune --all
cd ../
docker compose -f compose.yaml -f overrides/compose.noproxy.yaml -f overrides/compose.mariadb.yaml -f overrides/compose.redis.yaml -f nitta_note_app/compose.override.yaml down
cd nitta_note_app/
FRAPPE_VERSION=v14.32.1 ERPNEXT_VERSION=version-14 docker buildx bake
cd ../
docker compose -f compose.yaml -f overrides/compose.noproxy.yaml -f overrides/compose.mariadb.yaml -f overrides/compose.redis.yaml -f nitta_note_app/compose.override.yaml up -d
docker compose exec backend bench --site nitta.localhost migrate
docker compose restart backend
yes|docker image prune
