"""Configurazione da variabili d'ambiente."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


@dataclass
class Settings:
    mqtt_host: str = field(default_factory=lambda: _env("MQTT_HOST", "localhost"))
    mqtt_port: int = field(default_factory=lambda: int(_env("MQTT_PORT", "1883")))
    mqtt_user: str = field(default_factory=lambda: _env("MQTT_USER", ""))
    mqtt_pass: str = field(default_factory=lambda: _env("MQTT_PASS", ""))
    api_token: str = field(default_factory=lambda: _env("API_TOKEN", ""))
    db_path: str = field(default_factory=lambda: _env("DB_PATH", "./data/manipmasta.db"))
    topic_prefix: str = field(default_factory=lambda: _env("TOPIC_PREFIX", "manipmasta").rstrip("/"))
    resp_timeout: float = field(default_factory=lambda: float(_env("RESP_TIMEOUT", "2.0")))

    def topic(self, name: str) -> str:
        return f"{self.topic_prefix}/{name}"
