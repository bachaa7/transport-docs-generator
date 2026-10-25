#!/usr/bin/env bash
# Запуск сервиса документов на Linux.
# --host 0.0.0.0 — чтобы форма была доступна не только с самого сервера,
#        но и с других ПК в сети (127.0.0.1 принимает только локальные соединения).
set -e

# Где лежат шаблоны и справочники (скопируйте сюда содержимое input_dir с Windows):
export INPUT_DIR="${INPUT_DIR:-/opt/docgen/input_dir}"
# Куда сервис складывает готовые документы:
export OUTPUT_DIR="${OUTPUT_DIR:-/opt/docgen/output}"

# Порт сервиса. Форма открывается на http://<host>:8077/form и шлёт данные прямо в /generate.
exec uvicorn main:app --host 0.0.0.0 --port 8077
