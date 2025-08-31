import logging
import time
import webbrowser

import requests

from .config import DEVICE_CODE_URL, CLIENT_ID, headers, TOKEN_URL


def get_device_code():
    response = requests.post(
        DEVICE_CODE_URL,
        json={
            "client_id": CLIENT_ID,
            "scope": "profile",
        },
        headers=headers,
    )

    if response.status_code != 200:
        raise Exception(f"Ошибка запроса: {response.status_code} - {response.text}")

    return response.json()


def poll_for_token(device_code, interval, expires_in):
    for _ in range(int(expires_in / interval)):
        response = requests.post(
            TOKEN_URL,
            data={
                "client_id": CLIENT_ID,
                "device_code": device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            },
        )
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 400:
            error = response.json().get("error")
            if error == "authorization_pending":
                time.sleep(interval)
                continue
            else:
                raise Exception(f"Ошибка: {error}")
        else:
            response.raise_for_status()
    raise Exception("Время авторизации истекло")


def authorize_via_device_code():
    device = get_device_code()
    logging.info(f"🔗 Перейди по ссылке: {device['verification_uri_complete']}")
    webbrowser.open(device["verification_uri_complete"])
    return poll_for_token(
        device["device_code"], device["interval"], device["expires_in"]
    )
