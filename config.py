"""Shared configuration. Demo values only — replace with your own targets."""

import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_IDS: list[int] = [
    int(value) for value in os.getenv("CHAT_IDS", "").split(",") if value.strip()
]

REPORT_TIME_HOUR = 8
REPORT_TIME_MINUTE = 0
REPORT_TIMEZONE = os.getenv("REPORT_TIMEZONE", "Europe/Minsk")

SITES = [
    {"url": "https://example.com", "label": "example.com"},
]

SERVERS = [
    # {
    #     "label": "app-1",
    #     "host": "203.0.113.10",
    #     "port": 9101,
    #     "token": os.getenv("AGENT_TOKEN", ""),
    # },
]

SSL_WARN_DAYS = 30
SSL_CRITICAL_DAYS = 14

CPU_WARN_PCT = 80
RAM_FREE_WARN_PCT = 20
DISK_FREE_WARN_PCT = 15

HTTP_TIMEOUT = 15
AGENT_TIMEOUT = 5
