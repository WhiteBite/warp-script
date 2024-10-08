import base64
import json
import os
import requests
from datetime import datetime
from flask import Flask, render_template, send_file
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import serialization
from io import BytesIO

app = Flask(__name__)

# Создание директории для конфигураций
os.makedirs(os.path.expanduser("~/.cloudshell"), exist_ok=True)
with open(os.path.expanduser("~/.cloudshell/no-apt-get-warning"), 'w') as f:
    pass


# Функция для генерации ключей WireGuard
def generate_keys():
    private_key = x25519.X25519PrivateKey.generate()
    public_key = private_key.public_key()

    priv_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption())
    pub_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )

    return base64.b64encode(priv_bytes).decode(), base64.b64encode(
        pub_bytes).decode()


api = "https://api.cloudflareclient.com/v0i1909051800"


# Функция для выполнения запросов к API
def ins(method, endpoint, data=None, json=None, headers=None):
    if headers is None:
        headers = {'User-Agent': '', 'Content-Type': 'application/json'}
    else:
        headers.update({'User-Agent': '', 'Content-Type': 'application/json'})

    try:
        response = requests.request(method,
                                    f"{api}/{endpoint}",
                                    headers=headers,
                                    data=data,
                                    json=json)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Ошибка запроса: {e}")
        if e.response is not None:
            print(f"Ответ сервера: {e.response.text}")
        return None


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/download')
def download():
    priv, pub = generate_keys()

    registration_payload = {
        "install_id": "",
        "tos": datetime.utcnow().isoformat() + "Z",
        "key": pub,
        "fcm_token": "",
        "type": "ios",
        "locale": "en_US"
    }

    response = ins("POST", "reg", json=registration_payload)
    if response is None or 'result' not in response:
        return "Ошибка при регистрации", 500

    id = response['result']['id']
    token = response['result']['token']

    response = ins("PATCH",
                   f"reg/{id}",
                   headers={"Authorization": f"Bearer {token}"},
                   json={"warp_enabled": True})
    if response is None or 'result' not in response or 'config' not in response[
            'result']:
        return "Ошибка при обновлении конфигурации", 500

    peers = response['result']['config'].get('peers', [])
    if not peers:
        return "Ошибка: отсутствуют пиры в конфигурации", 500

    peer_pub = peers[0].get('public_key')
    peer_endpoint = peers[0].get('endpoint', {}).get('host')

    addresses = response['result']['config']['interface'].get('addresses', {})
    if 'v4' not in addresses or 'v6' not in addresses:
        return "Ошибка: недостаточно адресов в конфигурации", 500

    client_ipv4 = addresses['v4']
    client_ipv6 = addresses['v6']
    port = peer_endpoint.split(":")[-1] if peer_endpoint else "51820"
    peer_endpoint = "162.159.193.5"

    # Задание фиксированных значений
    S1, S2, H1, H2, H3, H4 = 0, 0, 1, 2, 3, 4
    Jc, Jmin, Jmax = 120, 23, 911

    # Формирование конфигурации
    conf = f"""
[Interface]
PrivateKey = {priv}
S1 = {S1}
S2 = {S2}
Jc = {Jc}
Jmin = {Jmin}
Jmax = {Jmax}
H1 = {H1}
H2 = {H2}
H3 = {H3}
H4 = {H4}
Address = {client_ipv4}, {client_ipv6}
DNS = 1.1.1.1, 2606:4700:4700::1111, 1.0.0.1, 2606:4700:4700::1001

[Peer]
PublicKey = {peer_pub}
AllowedIPs = 0.0.0.0/0, ::/0
Endpoint = {peer_endpoint}:{port}
"""

    # Кодирование в base64
    conf_base64 = base64.b64encode(conf.encode()).decode()
    return send_file(BytesIO(conf.encode()),
                     as_attachment=True,
                     download_name='WARP.conf',
                     mimetype='text/plain')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
