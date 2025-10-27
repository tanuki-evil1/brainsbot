from typing import Union

from app.adapters.protocols.wireguard.manager import WireGuardManager
from app.adapters.protocols.xray.manager import XrayManager
from app.entities import Protocol, Server


class ProtocolFactory:
    """Фабрика для создания менеджеров протоколов"""

    @staticmethod
    def create_manager(protocol: Protocol, server: Server) -> Union[WireGuardManager, XrayManager]:
        """
        Создает и возвращает менеджер для указанного протокола

        Args:
            protocol: Тип протокола (Protocol.WIREGUARD или Protocol.XRAY)

        Returns:
            Экземпляр менеджера протокола (WireGuardManager или XrayManager)

        Raises:
            ValueError: Если передан неподдерживаемый протокол
        """
        if protocol == Protocol.WIREGUARD:
            return WireGuardManager(
                host=server.host,
                user=server.admin_username,
                password=server.password,
                server_public_key=server.additional_info["wg_public_key"],
                preshared_key=server.additional_info["wg_preshared_key"],
            )
        elif protocol == Protocol.XRAY:
            return XrayManager(
                host=server.host,
                user=server.admin_username,
                password=server.password,
                port=server.port,
                server_public_key=server.additional_info["xray_public_key"],
                server_short_id=server.additional_info["xray_short_id"],
                server_name=server.additional_info["xray_sni"],
            )
        else:
            raise ValueError(f"Неподдерживаемый протокол: {protocol}")
