#!/bin/bash

# Простой вывод информации
echo "Скрипт запускается..."

# Проверка доступности curl
if ! command -v curl &> /dev/null; then
    echo "curl не установлен. Необходимо для выполнения запросов."
    exit 1
fi

# Выполнение запроса к API
api="https://api.cloudflareclient.com/v0i1909051800"
response=$(curl -s -X POST "${api}/reg" -H "Content-Type: application/json" -d "{\"install_id\":\"\",\"tos\":\"$(date -u +%FT%T.000Z)\",\"key\":\"dummy_key\",\"fcm_token\":\"\",\"type\":\"ios\",\"locale\":\"en_US\"}")

# Проверка ответа
if [[ $? -ne 0 ]]; then
    echo "Ошибка при обращении к API."
    exit 1
fi

# Проверка, получен ли ответ
if [[ -z "$response" ]]; then
    echo "Получен пустой ответ от API."
    exit 1
fi

# Проверка на наличие ошибок в ответе
error_message=$(echo "$response" | jq -r '.error.message // empty')
if [[ -n "$error_message" ]]; then
    echo "Ошибка от API: $error_message"
    exit 1
fi

# Выводим ответ
echo "Ответ от API:"
echo "$response" | jq
