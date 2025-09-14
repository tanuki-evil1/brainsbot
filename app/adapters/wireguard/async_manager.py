import asyncio
import ipaddress
import json
from datetime import datetime
from io import StringIO
from typing import Any, Optional

import asyncssh
import wgconfig

from app import entities
from app.adapters.wireguard import templates


class AsyncWireGuardClientManager:
    """Асинхронный менеджер клиентов WireGuard"""

    def __init__(self, host: str, user: str, password: str):
        self.host = host
        self.user = user
        self.password = password
        self.server_public_key = "9tVJPFMkqDg5rCzpQO9BCW9mQTTF6bxuNP+7pz+EG28="
        self.preshared_key = "oKq1Anglz/Ve4NeQL8Dghl7TcQPizyvegB6yc5vDjqA="
        self._connection: asyncssh.SSHClientConnection | None = None

        # Отключаем отладочные логи asyncssh
        asyncssh.set_log_level("WARNING")

    async def __aenter__(self) -> "AsyncWireGuardClientManager":
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

    async def __aexit__(self, exc_type: Optional[type], exc_val: Optional[Exception], exc_tb: Optional[Any]) -> None:
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

    async def _find_available_ip(self, reserved_ips: list[str]) -> str:
        """Находит свободный IP адрес из пула адресов"""
        # Получаем текущую конфигурацию WireGuard
        wg_config = await self._run_command("docker exec -i amnezia-awg cat /opt/amnezia/awg/wg0.conf")

        # Парсим используемые IP адреса из конфигурации
        used_ips = set()
        for line in wg_config.split("\n"):
            line = line.strip()
            if line.startswith("AllowedIPs = "):
                ip_part = line.split("AllowedIPs = ")[1].strip()
                ip_only = ip_part.split("/")[0]

                used_ips.add(ipaddress.IPv4Address(ip_only))

        # Добавляем переданные забронированные IP адреса
        for reserved_ip in reserved_ips:
            ip_only = reserved_ip.split("/")[0]
            used_ips.add(ipaddress.IPv4Address(ip_only))

        # Используем стандартную сеть 10.8.1.0/24 для VPN
        network = ipaddress.IPv4Network("10.8.1.0/24")
        # Резервируем .1 для сервера
        used_ips.add(ipaddress.IPv4Address("10.8.1.1"))

        # Ищем первый свободный IP в сети
        for ip in network.hosts():
            if ip not in used_ips:
                return f"{ip}/32"

        # Если не найден свободный IP, поднимаем исключение
        raise RuntimeError("Нет доступных IP адресов в сети")

    async def create_config(self, username: str = "Anonym", ips: list[str] = []) -> entities.WireGuardUserConfig:
        # Находим свободный IP адрес с учетом забронированных
        allowed_ip = await self._find_available_ip(ips)

        client_private_key = await self._run_command("docker exec -i amnezia-awg wg genkey")
        client_public_key = await self._run_command(
            f"docker exec -i amnezia-awg bash -c \"echo '{client_private_key}' | wg pubkey\""
        )
        key_config = templates.OUTPUT_TEMPLATE.format(
            client_private_key=client_private_key,
            preshared_key=self.preshared_key,
            allowed_ip=allowed_ip,
            wireguard_server_public_key=self.server_public_key,
        )
        return entities.WireGuardUserConfig(
            client_public_key=client_public_key, access_key=key_config, allowed_ip=allowed_ip, username=username
        )

    async def add_user(self, user_config: entities.WireGuardUserConfig) -> None:
        wg_config = await self._run_command("docker exec -i amnezia-awg cat /opt/amnezia/awg/wg0.conf")
        config_io = StringIO(wg_config)
        wc = wgconfig.WGConfig()
        wc.read_from_fileobj(config_io)
        if user_config.client_public_key in wc.get_peers():
            return

        peer_config = templates.PEER_TEMPLATE.format(
            client_public_key=user_config.client_public_key,
            preshared_key=self.preshared_key,
            allowed_ip=user_config.allowed_ip,
        )

        client_config = templates.CLIENT_TEMPLATE.format(
            client_public_key=user_config.client_public_key,
            client_name=user_config.username,
            creation_date=datetime.now().strftime("%a %b %d %H:%M:%S %Y"),
        )

        clients_raw = await self._run_command("docker exec -i amnezia-awg cat /opt/amnezia/awg/clientsTable")
        clients_data = json.loads(clients_raw)

        new_client = json.loads(client_config)
        for client in clients_data:
            if client.get("clientId") == new_client.get("clientId"):
                break
        else:
            clients_data.append(new_client)

        updated_json = json.dumps(clients_data, indent=4, ensure_ascii=False).replace("'", "'\"'\"'")

        await self._run_command(f"echo '{updated_json}' | docker exec -i amnezia-awg tee /opt/amnezia/awg/clientsTable")
        await self._run_command(f"echo '{peer_config}' | docker exec -i amnezia-awg tee -a /opt/amnezia/awg/wg0.conf")
        await self._run_command(
            "docker exec -i amnezia-awg bash -c 'wg syncconf wg0 <(wg-quick strip /opt/amnezia/awg/wg0.conf)'"
        )

    async def remove_user(self, public_key: str) -> None:
        wg_config = await self._run_command("docker exec -i amnezia-awg cat /opt/amnezia/awg/wg0.conf")

        config_io = StringIO(wg_config)
        wc = wgconfig.WGConfig()
        wc.read_from_fileobj(config_io)
        if public_key in wc.get_peers():
            wc.del_peer(public_key)
            output_io = StringIO()
            wc.write_to_fileobj(output_io)
            new_config = output_io.getvalue()
            await self._run_command(f"echo '{new_config}' | docker exec -i amnezia-awg tee /opt/amnezia/awg/wg0.conf")
            await self._run_command(
                "docker exec -i amnezia-awg bash -c 'wg syncconf wg0 <(wg-quick strip /opt/amnezia/awg/wg0.conf)'"
            )

        # Обновляем clientsTable - удаляем клиента с указанным public key
        clients_raw = await self._run_command("docker exec -i amnezia-awg cat /opt/amnezia/awg/clientsTable")
        clients_data = json.loads(clients_raw)

        updated_clients = [client for client in clients_data if client.get("clientId") != public_key]
        updated_json = json.dumps(updated_clients, indent=4, ensure_ascii=False).replace("'", "'\"'\"'")

        await self._run_command(f"echo '{updated_json}' | docker exec -i amnezia-awg tee /opt/amnezia/awg/clientsTable")


async def main():
    async with AsyncWireGuardClientManager(host="94.228.168.225", user="root", password="jiESCyLdYUX0") as manager:
        # user_config = await manager.create_config(username="test", ips=["10.8.1.75/32"])
        # await manager.add_user(user_config)
        await manager.remove_user("Giwphk/FYcQQH2w4k86Gg9ykaulOQrLg/cTNbq+bfXA=")


if __name__ == "__main__":
    asyncio.run(main())
