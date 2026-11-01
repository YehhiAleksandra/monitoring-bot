# Monitoring Bot (demo)

Source-available demo of a small self-hosted monitoring stack for your own
sites and servers: one Telegram bot + one HTTP agent per server.

This repository is a **view-only showcase**. See [LICENSE](LICENSE) before you
do anything with the code.

## What it does

```text
        every day at 08:00 (configurable)
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
  HTTPS + TLS check          agent :9101
  (status, days left)        (CPU / RAM / disk)
        └────────────┬────────────┘
                     ▼
            one Telegram message
```

- checks every site from `SITES`: HTTP status and days until the TLS
  certificate expires;
- pulls CPU / RAM / disk metrics from each server that runs `agent.py`;
- sends one compact report to the configured Telegram chats;
- `/report` sends the same report on demand, `/status` shows the schedule.

## What is not in the demo

The production build keeps the following private, so this repository is not a
drop-in replacement for it:

- incident journal with open/resolve lifecycle and escalation;
- multi-recipient routing and quiet hours;
- per-partition alert thresholds and history;
- dashboard and metrics retention;
- deployment hooks and alerting integrations.

## Quick start

Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

export BOT_TOKEN="123456:your-token"
export CHAT_IDS="123456789"        # comma-separated
python bot.py
```

Edit `SITES` in `config.py` — the demo ships with `https://example.com` only.
`/status` and `/report` work as soon as the bot is running.

### Server agent

On every monitored server:

```bash
pip install psutil
export AGENT_TOKEN="$(python -c 'import secrets; print(secrets.token_hex(32))')"
python agent.py                    # listens on 0.0.0.0:9101
```

Add the server to `SERVERS` in `config.py` with the same `AGENT_TOKEN`. The
bot never sends the raw token: it sends `HMAC-SHA256(token, "metrics")` as a
query parameter, and the agent compares it in constant time. Keep port 9101
closed to the internet or restrict it to the bot's address.

Systemd units are in [`deploy/`](deploy).

## Tests

```bash
python -m unittest discover -s tests -v
```

## License

Source-available, viewing and evaluation only. Copying into another product,
redistribution and commercial use are not permitted. For a commercial license,
contact the author.

---

# Мониторинг-бот (демо)

Демо-витрина небольшого self-hosted мониторинга: Telegram-бот и HTTP-агент
на каждом сервере.

- проверка HTTP и срока SSL для сайтов из `SITES`;
- метрики CPU / RAM / диск с серверов, где запущен `agent.py`;
- ежедневный отчёт в Telegram, команды `/report` и `/status`.

**Чего нет в демо** (осталось в приватной версии): журнал инцидентов и
эскалация, маршрутизация получателей, пороги по разделам диска, дашборд и
хранение метрик, хуки деплоя.

Лицензия: исходники открыты для просмотра и ознакомления; копирование,
распространение и коммерческое использование запрещены.
