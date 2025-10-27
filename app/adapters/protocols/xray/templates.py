XRAY_CLIENT = """{{
    "log": {{
        "loglevel": "error"
    }},
    "inbounds": [
        {{
            "listen": "127.0.0.1",
            "port": 10808,
            "protocol": "socks",
            "settings": {{
                "udp": true
            }}
        }}
    ],
    "outbounds": [
        {{
            "protocol": "vless",
            "settings": {{
                "vnext": [
                    {{
                        "address": "{server_ip_address}",
                        "port": {server_port},
                        "users": [
                            {{
                                "id": "{user_uuid}",
                                "flow": "xtls-rprx-vision",
                                "encryption": "none"
                            }}
                        ]
                    }}
                ]
            }},
            "streamSettings": {{
                "network": "tcp",
                "security": "reality",
                "realitySettings": {{
                    "fingerprint": "chrome",
                    "serverName": "{server_name}",
                    "publicKey": "{server_public_key}",
                    "shortId": "{server_short_id}",
                    "spiderX": ""
                }}
            }}
        }}
    ]
}}"""

SHORT_XRAY_CLIENT = """vless://{user_uuid}@{server_ip_address}:{server_port}?encryption=none&flow=xtls-rprx-vision&type=tcp&security=reality&pbk={server_public_key}&sid={server_short_id}&fp=chrome&sni={server_name}#REALITY_Server"""

CLIENT_TEMPLATE = """
{{
    "clientId": "{client_public_key}",
    "userData": {{
        "clientName": "{client_name}",
        "creationDate": "{creation_date}"
    }}
}}
"""
