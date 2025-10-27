import json
import uuid
from datetime import datetime
from typing import Any

import asyncssh

from app import entities
from app.adapters.protocols.xray import templates


class XrayManager:
    def __init__(self, host: str, user: str, password: str, port: int, server_public_key: str, server_short_id: str, server_name: str):
        self.host = host
        self.user = user
        self.password = password
        self.port = port
        self.server_public_key = server_public_key
        self.server_short_id = server_short_id
        self.server_name = server_name

    # Отключаем отладочные логи asyncssh
        asyncssh.set_log_level("WARNING")

    async def __aenter__(self) -> "XrayManager":
        """Асинхронный контекстный менеджер - вход"""
        self._connection = await asyncssh.connect(
            host=self.host,
            username=self.user,
            password=self.password,
            known_hosts=None,  # Отключаем проверку known_hosts для простоты
            client_keys=None,  # Отключаем автоматические ключи
            compression_algs=None,  # Отключаем сжатие для меньшего количества логов
        )
        return self

    async def __aexit__(self, exc_type: type | None, exc_val: Exception | None, exc_tb: Any | None) -> None:
        """Асинхронный контекстный менеджер - выход"""
        if self._connection:
            self._connection.close()
            await self._connection.wait_closed()


    async def _run_command(self, command: str) -> str:
        """Выполнить команду на удаленном сервере"""
        if not self._connection:
            raise RuntimeError("Connection not established. Use async context manager.")

        result = await self._connection.run(command)
        if result.exit_status != 0:
            stderr_text = "No error details"
            if result.stderr:
                if isinstance(result.stderr, str):
                    stderr_text = result.stderr
                else:
                    stderr_text = str(result.stderr)
            raise RuntimeError(f"Command failed: {command}\nError: {stderr_text}")

        stdout = result.stdout
        if stdout is None:
            return ""

        if isinstance(stdout, str):
            return stdout.strip()
        else:
            # Handle bytes or other types
            return str(stdout).strip()


    async def create_config(self, username: str, **kwargs) -> entities.XrayUserConfig:
        user_uuid = uuid.uuid4()
        key = templates.SHORT_XRAY_CLIENT.format(
            server_ip_address=self.host,
            server_port=self.port,
            user_uuid=user_uuid,
            server_name=self.server_name,
            server_public_key=self.server_public_key,
            server_short_id=self.server_short_id,
        )
        return entities.XrayUserConfig(uuid=user_uuid, key=key, username=username)


    async def add_user(self, user_config: entities.XrayUserConfig) -> None:
        server_raw = await self._run_command("docker exec -i amnezia-xray cat /opt/amnezia/xray/server.json")
        server_data = json.loads(server_raw)
        new_user = {
            "id":str(user_config.uuid),
            "flow": "xtls-rprx-vision"
            }
        server_data["inbounds"][0]["settings"]["clients"].append(new_user)
        json_xray = json.dumps(server_data, indent=4, ensure_ascii=False).replace("'", "'\"'\"'")
        client_config = templates.CLIENT_TEMPLATE.format(
            client_public_key=user_config.uuid,
            client_name=user_config.username,
            creation_date=datetime.now().strftime("%a %b %d %H:%M:%S %Y"),
        )

        clients_raw = await self._run_command("docker exec -i amnezia-xray cat /opt/amnezia/xray/clientsTable")
        clients_data = json.loads(clients_raw)

        new_client = json.loads(client_config)
        for client in clients_data:
            if client.get("clientId") == new_client.get("clientId"):
                break
        else:
            clients_data.append(new_client)

        updated_json = json.dumps(clients_data, indent=4, ensure_ascii=False).replace("'", "'\"'\"'")
        print(updated_json)

        await self._run_command(f"echo '{updated_json}' | docker exec -i amnezia-xray tee /opt/amnezia/xray/clientsTable")
        await self._run_command(f"echo '{json_xray}' | docker exec -i amnezia-xray tee /opt/amnezia/xray/server.json")

        # Перезапускаем контейнер для применения изменений
        await self._run_command("docker restart amnezia-xray")

    async def remove_user(self, user_uuid: uuid.UUID) -> None:
        server_raw = await self._run_command("docker exec -i amnezia-xray cat /opt/amnezia/xray/server.json")
        server_data = json.loads(server_raw)
        for client in server_data["inbounds"][0]["settings"]["clients"]:
            if client.get("id") == str(user_uuid):
                server_data["inbounds"][0]["settings"]["clients"].remove(client)
                break

        updated_json = json.dumps(server_data, indent=4, ensure_ascii=False).replace("'", "'\"'\"'")
        await self._run_command(f"echo '{updated_json}' | docker exec -i amnezia-xray tee /opt/amnezia/xray/server.json")
        # Обновляем clientsTable - удаляем клиента с указанным public key
        clients_raw = await self._run_command("docker exec -i amnezia-xray cat /opt/amnezia/xray/clientsTable")
        clients_data = json.loads(clients_raw)

        updated_clients = [client for client in clients_data if client.get("clientId") != str(user_uuid)]
        updated_json = json.dumps(updated_clients, indent=4, ensure_ascii=False).replace("'", "'\"'\"'")

        await self._run_command(f"echo '{updated_json}' | docker exec -i amnezia-xray tee /opt/amnezia/xray/clientsTable")
        await self._run_command("docker restart amnezia-xray")
