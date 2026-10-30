#!/bin/sh
# Roda uma vez, na criação do volume do Postgres.
# Cria o usuário que a aplicação usa para consultar: só SELECT, só no schema
# public, transações somente leitura e tempo máximo por consulta. É a camada
# de defesa que vale mesmo se o validador de SQL deixar algo passar.
set -eu

psql -v ON_ERROR_STOP=1 \
    --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    -v leitor="$POSTGRES_LEITOR_USUARIO" -v senha="$POSTGRES_LEITOR_SENHA" \
    -v dono="$POSTGRES_USER" -v banco="$POSTGRES_DB" <<'SQL'
CREATE ROLE :"leitor" LOGIN PASSWORD :'senha';
ALTER ROLE :"leitor" SET default_transaction_read_only = on;
ALTER ROLE :"leitor" SET statement_timeout = '15s';

REVOKE ALL ON DATABASE :"banco" FROM PUBLIC;
GRANT CONNECT ON DATABASE :"banco" TO :"leitor";
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO :"leitor";

-- Tabelas que a carga criar depois em public já nascem legíveis pelo leitor.
ALTER DEFAULT PRIVILEGES FOR ROLE :"dono" IN SCHEMA public GRANT SELECT ON TABLES TO :"leitor";
SQL
