import json
import uuid
from datetime import datetime, timedelta

from vi_core import HttpClient

from app.settings import settings


class XuiClient:

    def __init__(self, base_url: str):
        self.http_client = HttpClient(base_url=base_url)

    async def login(self):
        url = "/login"
        response = await self.http_client.request(
            "POST", url, json={"username": settings.xui_username, "password": settings.xui_password}
        )
        return response.json()

    async def add_client(
        self,
        email: str,
        user_uuid: str,
        days: int = 30,
    ) -> None:
        await self.login()
        url = "/panel/api/inbounds/addClient"

        expiry_datetime = datetime.now() + timedelta(days=days)
        expiry_time = int(expiry_datetime.timestamp() * 1000)

        client_settings = {
            "clients": [
                {
                    "id": user_uuid,
                    "flow": "xtls-rprx-vision",
                    "email": email,
                    "limitIp": 0,
                    "totalGB": 0,
                    "expiryTime": expiry_time,
                    "enable": True,
                    "tgId": "",
                    "subId": user_uuid,
                    "comment": "",
                    "reset": 0
                }
            ]
        }

        data = {
            "id": "4",
            "settings": json.dumps(client_settings)
        }

        await self.http_client.request("POST", url, data=data)

    async def update_client(
        self,
        user_uuid: str,
        email: str,
    ):
        await self.login()
        url = f"/panel/api/inbounds/updateClient/{user_uuid}"
        expiry_datetime = datetime.now() + timedelta(days=30)
        expiry_time = int(expiry_datetime.timestamp() * 1000)

        client_settings = {
            "clients": [
                {
                    "id": user_uuid,
                    "flow": "xtls-rprx-vision",
                    "email": email,
                    "limitIp": 0,
                    "totalGB": 0,
                    "expiryTime": expiry_time,
                    "enable": True,
                    "tgId": "",
                    "subId": user_uuid,
                    "comment": "",
                    "reset": 0
                }
            ]
        }

        data = {
            "id": "4",
            "settings": json.dumps(client_settings)
        }

        response = await self.http_client.request("POST", url, data=data)
        return response.json()

# async def main():
#     client = XuiClient(http_client=HttpClient(base_url="http://144.31.16.145:22313/ZhOpx1y2ei2ONT8rmM"))
#     await client.login()
#     pprint.pprint(await client.update_client(
#         user_uuid=uuid.UUID("67b02297-2cfc-4f5c-9f9c-6601b7656d9a"),
#         email="hcid8fgv",
#     ))

# if __name__ == "__main__":
#     asyncio.run(main())


