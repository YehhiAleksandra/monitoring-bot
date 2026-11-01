#!/usr/bin/env python3
"""Telegram monitoring bot: HTTP/TLS checks for sites and agent metrics for servers."""

import asyncio
import logging
import socket
import ssl
from datetime import datetime

import aiohttp
import certifi
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import (
    AGENT_TIMEOUT,
    BOT_TOKEN,
    CHAT_IDS,
    CPU_WARN_PCT,
    DISK_FREE_WARN_PCT,
    HTTP_TIMEOUT,
    RAM_FREE_WARN_PCT,
    REPORT_TIME_HOUR,
    REPORT_TIME_MINUTE,
    REPORT_TIMEZONE,
    SERVERS,
    SITES,
    SSL_CRITICAL_DAYS,
    SSL_WARN_DAYS,
)
from monitoring.core import (
    agent_token,
    http_ok,
    resource_level,
    ssl_days_left,
    ssl_level,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("monitoring_bot")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler(timezone=REPORT_TIMEZONE)

ICONS = {"ok": "✅", "warn": "⚠️", "critical": "🔴", "unknown": "❓"}


def get_ssl_days_left(hostname: str, port: int = 443) -> int | None:
    context = ssl.create_default_context(cafile=certifi.where())
    try:
        with socket.create_connection((hostname, port), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as secure:
                not_after = secure.getpeercert()["notAfter"]
                return ssl_days_left(not_after)
    except Exception as error:
        log.warning("SSL check failed for %s: %s", hostname, error)
        return None


async def check_http(url: str) -> tuple[bool, int | None]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)
            ) as response:
                return http_ok(response.status), response.status
    except Exception as error:
        log.warning("HTTP check failed for %s: %s", url, error)
        return False, None


async def fetch_server_metrics(server: dict) -> dict | None:
    signature = agent_token(server["token"])
    url = f"http://{server['host']}:{server['port']}/metrics?token={signature}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=AGENT_TIMEOUT)
            ) as response:
                if response.status == 200:
                    return await response.json()
                log.warning("Agent %s returned HTTP %s", server["host"], response.status)
                return None
    except Exception as error:
        log.warning("Agent %s unreachable: %s", server["host"], error)
        return None


def format_server_block(label: str, metrics: dict | None) -> str:
    if metrics is None:
        return f"🖥 <b>{label}</b>\n   ❌ Агент недоступен"

    cpu = metrics["cpu_percent"]
    ram = metrics["ram"]
    disk = metrics["disk"]
    lines = [
        f"🖥 <b>{label}</b>",
        f"   {ICONS[resource_level(100 - cpu, 100 - CPU_WARN_PCT)]} CPU: {cpu}%",
        f"   {ICONS[resource_level(ram['free_percent'], RAM_FREE_WARN_PCT)]} "
        f"RAM свободно: {ram['free_percent']}% ({ram['free_gb']} ГБ)",
        f"   {ICONS[resource_level(disk['free_percent'], DISK_FREE_WARN_PCT)]} "
        f"Диск / свободно: {disk['free_percent']}% ({disk['free_gb']} ГБ)",
    ]
    return "\n".join(lines)


async def build_report() -> str:
    lines = [
        "📊 <b>Ежедневный отчёт мониторинга</b>",
        f"🕒 {datetime.now().strftime('%d.%m.%Y %H:%M')}",
        "",
    ]

    http_results, agent_results = await asyncio.gather(
        asyncio.gather(*(check_http(site["url"]) for site in SITES)),
        asyncio.gather(*(fetch_server_metrics(server) for server in SERVERS)),
    )

    site_lines = []
    for site, (ok, status) in zip(SITES, http_results):
        hostname = site["url"].split("://", 1)[-1].rstrip("/")
        days = get_ssl_days_left(hostname)
        level = ssl_level(days, SSL_WARN_DAYS, SSL_CRITICAL_DAYS)
        if not ok:
            site_lines.append(f"🔴 {site['label']} — HTTP {status or 'недоступен'}")
        site_lines.append(
            f"{ICONS[level]} {site['label']} — SSL {days if days is not None else '?'} дн."
        )

    lines.append("🌐 <b>Сайты и сертификаты:</b>")
    lines.extend(site_lines)
    lines.append("")
    lines.append("🖥 <b>Серверы:</b>")
    for server, metrics in zip(SERVERS, agent_results):
        lines.append(format_server_block(server["label"], metrics))
        lines.append("")
    lines.append("📎 <i>Отчёт сформирован автоматом</i>")
    return "\n".join(lines)


async def send_report() -> None:
    try:
        text = await build_report()
        for chat_id in CHAT_IDS:
            await bot.send_message(
                chat_id, text, parse_mode="HTML", disable_web_page_preview=True
            )
    except Exception as error:
        log.error("Failed to send report: %s", error)


@dp.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(
        "👋 <b>Monitoring Bot запущен!</b>\n\n"
        "/report — отчёт сейчас\n"
        "/status — расписание и цели\n",
        parse_mode="HTML",
    )


@dp.message(Command("report"))
async def cmd_report(message: Message) -> None:
    status = await message.answer("⏳ Собираю данные...")
    try:
        await status.edit_text(
            await build_report(), parse_mode="HTML", disable_web_page_preview=True
        )
    except Exception as error:
        await status.edit_text(f"❌ Ошибка: {error}")


@dp.message(Command("status"))
async def cmd_status(message: Message) -> None:
    jobs = scheduler.get_jobs()
    next_run = jobs[0].next_run_time.strftime("%d.%m.%Y %H:%M") if jobs else "нет задач"
    await message.answer(
        "⚙️ <b>Статус бота</b>\n\n"
        "🟢 Работает\n"
        f"📅 Следующий отчёт: {next_run}\n"
        f"🌐 Сайтов: {len(SITES)}\n"
        f"🖥 Серверов: {len(SERVERS)}\n"
        f"👥 Получателей: {len(CHAT_IDS)}",
        parse_mode="HTML",
    )


async def main() -> None:
    scheduler.add_job(
        send_report,
        "cron",
        hour=REPORT_TIME_HOUR,
        minute=REPORT_TIME_MINUTE,
        id="daily_report",
    )
    scheduler.start()
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN is empty; set it before starting the bot")
    asyncio.run(main())
