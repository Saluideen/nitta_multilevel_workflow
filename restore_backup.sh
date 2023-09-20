# Restore Backup
cd ../
docker cp nitta_note_app/backup/20230418_111844-nitta_ideendevelopers_xyz-database.sql.gz $(docker compose ps -q backend):/tmp
docker compose exec backend bench --site nitta.localhost restore /tmp/20230418_111844-nitta_ideendevelopers_xyz-database.sql.gz --mariadb-root-password 123
docker compose exec backend bench --site nitta.localhost migrate
docker compose restart backend
