"""
Loga como admin e gera um novo token para o bot informado.
"""

import base64
import os

import requests

DEFAULT_BOT_NAME = "ingestion-bot"


def get_bot_jwt_token() -> str:
    host_port = os.environ["OPENMETADATA_HOST_PORT"].rstrip("/")
    bot_name = os.environ.get("OPENMETADATA_BOT_NAME", DEFAULT_BOT_NAME)
    admin_email = os.environ["OPENMETADATA_ADMIN_EMAIL"]
    admin_password = os.environ["OPENMETADATA_ADMIN_PASSWORD"]

    login_resp = requests.post(
        f"{host_port}/v1/users/login",
        json={
            "email": admin_email,
            "password": base64.b64encode(admin_password.encode()).decode(),
        },
        timeout=30,
    )
    login_resp.raise_for_status()
    access_token = login_resp.json()["accessToken"]
    headers = {"Authorization": f"Bearer {access_token}"}

    bot_resp = requests.get(f"{host_port}/v1/bots/name/{bot_name}", headers=headers, timeout=30)
    bot_resp.raise_for_status()
    bot_user_id = bot_resp.json()["botUser"]["id"]

    token_resp = requests.put(
        f"{host_port}/v1/users/generateToken/{bot_user_id}",
        headers=headers,
        json={"JWTTokenExpiry": "Unlimited"},
        timeout=30,
    )
    token_resp.raise_for_status()
    return token_resp.json()["JWTToken"]


if __name__ == "__main__":
    print(get_bot_jwt_token())
