"""Профили двух Kafka. Поправьте пути/пароли/bootstrap под себя."""
from __future__ import annotations

import os
import tempfile

from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    pkcs12,
)

# --- кластер A ---
CLUSTER_A = {
    "name": "A",
    "bootstrap": "broker-a1:9092,broker-a2:9092",
    "truststore_pfx": r"C:\path\to\a-truststore.pfx",
    "truststore_pass": "pass",
    "keystore_pfx": r"C:\path\to\a-keystore.pfx",
    "keystore_pass": "pass",
}

# --- кластер B ---
CLUSTER_B = {
    "name": "B",
    "bootstrap": "broker-b1:9092,broker-b2:9092",
    "truststore_pfx": r"C:\path\to\b-truststore.pfx",
    "truststore_pass": "pass",
    "keystore_pfx": r"C:\path\to\b-keystore.pfx",
    "keystore_pass": "pass",
}

CLUSTERS = {"A": CLUSTER_A, "B": CLUSTER_B}


def load_pfx(path, password):
    with open(path, "rb") as f:
        return pkcs12.load_key_and_certificates(f.read(), password.encode())


def prepare_ssl_files(cluster: dict):
    tmp = tempfile.mkdtemp(prefix=f"kafka_ssl_{cluster['name']}_")

    _k, trust_cert, trust_additional = load_pfx(
        cluster["truststore_pfx"], cluster["truststore_pass"]
    )
    ca_path = os.path.join(tmp, "ca.pem")
    certs = []
    if trust_cert is not None:
        certs.append(trust_cert)
    certs.extend(trust_additional or [])
    if not certs:
        raise SystemExit(f"[{cluster['name']}] в truststore нет сертификатов")
    with open(ca_path, "wb") as f:
        for c in certs:
            f.write(c.public_bytes(Encoding.PEM))

    client_key, client_cert, client_additional = load_pfx(
        cluster["keystore_pfx"], cluster["keystore_pass"]
    )
    if client_key is None or client_cert is None:
        raise SystemExit(f"[{cluster['name']}] в keystore нет client key/cert")

    cert_path = os.path.join(tmp, "client_cert.pem")
    key_path = os.path.join(tmp, "client_key.pem")
    with open(cert_path, "wb") as f:
        f.write(client_cert.public_bytes(Encoding.PEM))
        for c in client_additional or []:
            f.write(c.public_bytes(Encoding.PEM))
    with open(key_path, "wb") as f:
        f.write(
            client_key.private_bytes(
                Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()
            )
        )
    return ca_path, cert_path, key_path, tmp


def build_ssl_conf(bootstrap: str, ca: str, cert: str, keyfile: str) -> dict:
    return {
        "bootstrap_servers": bootstrap,
        "security_protocol": "SSL",
        "ssl_cafile": ca,
        "ssl_certfile": cert,
        "ssl_keyfile": keyfile,
        "enable_auto_commit": False,
        "consumer_timeout_ms": 15000,
        "request_timeout_ms": 30000,
        "api_version_auto_timeout_ms": 30000,
    }
