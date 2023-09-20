# Create Site and Install Application
yes|docker builder prune --all
cd ../
docker compose -f compose.yaml -f overrides/compose.noproxy.yaml -f overrides/compose.mariadb.yaml -f overrides/compose.redis.yaml -f nitta_note_app/compose.override.yaml down
FRAPPE_VERSION=v14.32.1 ERPNEXT_VERSION=version-14 docker buildx bake
cd nitta_note_app/
FRAPPE_VERSION=v14.32.1 ERPNEXT_VERSION=version-14 docker buildx bake
cd ../
docker compose -f compose.yaml -f overrides/compose.noproxy.yaml -f overrides/compose.mariadb.yaml -f overrides/compose.redis.yaml -f nitta_note_app/compose.override.yaml up -d
docker compose exec backend bench new-site nitta.localhost --mariadb-root-password 123 --admin-password Koll@m45
docker compose exec backend bench --site nitta.localhost install-app nitta_note_app
docker compose exec backend bench --site nitta.localhost set-config encryption_key xmYJaeGu-SKVNafFB2baJPgjVddKp9gUKjlvT8_KPio=
docker compose exec backend bench --site nitta.localhost enable-scheduler
