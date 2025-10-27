PEER_TEMPLATE = """
[Peer]
PublicKey = {client_public_key}
PresharedKey = {preshared_key}
AllowedIPs = {allowed_ip}"""

OUTPUT_TEMPLATE = """
[Interface]
Address = {allowed_ip}
DNS = 1.1.1.1, 1.1.0.1
PrivateKey = {client_private_key}
Jc = 4
Jmin = 10
Jmax = 50
S1 = 138
S2 = 123
H1 = 2109784424
H2 = 457947774
H3 = 1374400826
H4 = 1191593502

[Peer]
PublicKey = {wireguard_server_public_key}
PresharedKey = {preshared_key}
AllowedIPs = 0.0.0.0/0, ::/0
Endpoint = 94.228.168.225:37642
PersistentKeepalive = 25
""".strip()

CLIENT_TEMPLATE = """
{{
    "clientId": "{client_public_key}",
    "userData": {{
        "clientName": "{client_name}",
        "creationDate": "{creation_date}"
    }}
}}
"""