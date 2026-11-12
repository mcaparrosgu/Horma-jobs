#!/bin/bash
# Crea los dos roles de la aplicación y la base de pruebas.
#  - horma_migrador: propietario del esquema; aplica las migraciones.
#  - horma_app: lo usan la API y el worker; sin superusuario y sujeto a RLS.
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<SQL
CREATE ROLE horma_migrador LOGIN PASSWORD '${HORMA_MIGRADOR_PASSWORD}' NOSUPERUSER NOBYPASSRLS;
CREATE ROLE horma_app LOGIN PASSWORD '${HORMA_APP_PASSWORD}' NOSUPERUSER NOBYPASSRLS;
CREATE DATABASE ${POSTGRES_DB}_test OWNER horma_migrador;
ALTER DATABASE ${POSTGRES_DB} OWNER TO horma_migrador;
SQL

for bd in "$POSTGRES_DB" "${POSTGRES_DB}_test"; do
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$bd" <<SQL
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT ALL ON SCHEMA public TO horma_migrador;
GRANT USAGE ON SCHEMA public TO horma_app;
SQL
done
