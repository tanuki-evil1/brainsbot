import ipaddress
import json
from app.adapters.wireguard import templates
from datetime import datetime
from fabric import Connection


class WireGuardClientManager:
    def __init__(self, host: str, user: str, password: str):
        self.conn = Connection(host=host, user=user, connect_kwargs={"password": password})
        self.server_public_key = "9tVJPFMkqDg5rCzpQO9BCW9mQTTF6bxuNP+7pz+EG28="
        self.preshared_key = "oKq1Anglz/Ve4NeQL8Dghl7TcQPizyvegB6yc5vDjqA="

    def add_user(self, username: str) -> str:
        with self.conn:
            client_private_key = self.conn.run("docker exec -i amnezia-awg wg genkey", hide=True).stdout.strip()
            client_public_key = self.conn.run(
                f"docker exec -i amnezia-awg bash -c \"echo '{client_private_key}' | wg pubkey\"", hide=True
            ).stdout.strip()

            ips = self.conn.run(
                "docker exec -i amnezia-awg cat /opt/amnezia/awg/wg0.conf | grep AllowedIPs", hide=True
            ).stdout
            last_ip = ipaddress.IPv4Network(ips.split("AllowedIPs = ")[-1].strip(), strict=False)
            allowed_ip = f"{last_ip.network_address + 1}/{last_ip.prefixlen}"

            peer_config = templates.PEER_TEMPLATE.format(
                client_public_key=client_public_key,
                preshared_key=self.preshared_key,
                allowed_ip=allowed_ip,
            )

            output_config: str = templates.OUTPUT_TEMPLATE.format(
                client_private_key=client_private_key,
                client_public_key=client_public_key,
                preshared_key=self.preshared_key,
                allowed_ip=allowed_ip,
                wireguard_server_public_key=self.server_public_key,
            )

            client_config = templates.CLIENT_TEMPLATE.format(
                client_public_key=client_public_key,
                client_name=username,
                creation_date=datetime.now().strftime("%a %b %d %H:%M:%S %Y"),
            )

            # Получаем содержимое файла клиентов (JSON массив в .txt файле)
            clients_raw = self.conn.run(
                "docker exec -i amnezia-awg cat /opt/amnezia/awg/clientsTable", hide=True
            ).stdout.strip()

            # Парсим JSON массив и добавляем нового клиента
            clients_data = json.loads(clients_raw)
            new_client = json.loads(client_config)
            clients_data.append(new_client)

            # Формируем обновленный JSON с красивым форматированием
            updated_json = json.dumps(clients_data, indent=4, ensure_ascii=False).replace("'", "'\"'\"'")

            self.conn.run(
                f"echo '{updated_json}' | docker exec -i amnezia-awg tee /opt/amnezia/awg/clientsTable", hide=True
            )

            # Добавляем новый peer в конфигурацию WireGuard
            self.conn.run(
                f"echo '{peer_config}' | docker exec -i amnezia-awg tee -a /opt/amnezia/awg/wg0.conf", hide=True
            )
            self.conn.run(
                "docker exec -i amnezia-awg bash -c 'wg syncconf wg0 <(wg-quick strip /opt/amnezia/awg/wg0.conf)'",
                hide=True,
            )
            return output_config
