"""Migrate all task text fields (title, description, feedback) to Ukrainian.

Usage:
    python scripts/migrate_tasks_to_ukrainian.py
"""

import asyncio
import json
import re
import sys
from pathlib import Path

import httpx
from sqlalchemy import select, update

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings  # noqa: E402
from app.core.logging import get_logger, setup_logging  # noqa: E402
from app.database.base import AsyncSessionLocal  # noqa: E402
from app.database.models.task import Task  # noqa: E402

setup_logging()
logger = get_logger(__name__)

# Known purely technical English words that should NOT trigger translation
_TECHNICAL_WORDS = frozenset(
    {
        "sql", "api", "url", "http", "https", "ftp", "www", "com", "net", "org",
        "pdf", "ssh", "git", "tcp", "udp", "dns", "vpn", "lan", "wan", "wifi",
        "cpu", "ram", "gpu", "usb", "hdmi", "vga", "dvi", "ssd", "hdd", "nvme",
        "ip", "id", "ok", "pc", "os", "ui", "db", "mac", "ios", "png", "jpg",
        "jpeg", "svg", "xml", "json", "html", "css", "js", "py", "exe", "dll",
        "bat", "cmd", "log", "tmp", "zip", "rar", "tar", "iso", "img",
    }
)


def _has_english_text(text: str | None) -> bool:
    """Return True if the text contains meaningful English (Latin alphabetic) content."""
    if not text:
        return False

    has_cyrillic = bool(re.search(r"[а-яА-ЯіІїЇєЄёЁґҐ]", text))
    latin_words = re.findall(r"\b[a-zA-Z]{3,}\b", text)

    if not latin_words:
        return False

    # Pure Latin text (no Cyrillic at all) → treat as English
    if not has_cyrillic:
        return True

    # Mixed: English is present when there are 2+ non-technical Latin words
    meaningful = [w for w in latin_words if w.lower() not in _TECHNICAL_WORDS]
    return len(meaningful) >= 2


async def _translate_fields(fields: dict[str, str]) -> dict[str, str]:
    """Translate the given fields to Ukrainian via OpenRouter. Returns translated dict."""
    if not settings.OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not configured")

    fields_json = json.dumps(fields, ensure_ascii=False, indent=2)

    prompt = f"""Перекладіть наступні текстові поля на українську мову.
Якщо поле вже на українській — поверніть без змін.
Зберігайте структуру тексту, переноси рядків, списки та форматування.
НЕ змінюйте: посилання, IP-адреси, шляхи до файлів, команди, назви файлів, числа, технічні ідентифікатори.

Поля (JSON):
{fields_json}

Поверніть ТІЛЬКИ валідний JSON-об'єкт з тими самими ключами та перекладеними значеннями."""

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://helpdesk.local",
                "X-Title": "HelpDesk Migration",
                "Content-Type": "application/json",
            },
            json={
                "model": "qwen/qwen3-32b",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Ти — перекладач текстів технічної підтримки. "
                            "Відповідай ТІЛЬКИ валідним JSON."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0,
                "response_format": {"type": "json_object"},
            },
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return json.loads(content)


async def _sync_notion(
    task_id: int,
    notion_page_id: str,
    title: str,
    description: str | None,
    feedback: str | None,
) -> None:
    """Update title, description and feedback in the Notion page."""
    if not settings.NOTION_TOKEN:
        return

    from notion_client import AsyncClient

    client = AsyncClient(auth=settings.NOTION_TOKEN)

    props: dict = {
        "Title": {"rich_text": [{"text": {"content": title}}]},
        "Description": {"rich_text": [{"text": {"content": description or ""}}]},
    }
    if feedback:
        props["Feedback"] = {"rich_text": [{"text": {"content": feedback}}]}

    await client.pages.update(page_id=notion_page_id, properties=props)
    logger.info("Notion synced task %d", task_id)


async def main() -> None:
    logger.info("=== Starting Ukrainian migration ===")

    # ------------------------------------------------------------------ #
    # 1. Load all tasks
    # ------------------------------------------------------------------ #
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Task))
        tasks: list[Task] = list(result.scalars().all())

    total = len(tasks)
    logger.info("Loaded %d tasks", total)

    # ------------------------------------------------------------------ #
    # 2. Detect fields needing translation and translate them
    # ------------------------------------------------------------------ #
    # pending: list of (task_snapshot, changed_field_values)
    pending: list[tuple[Task, dict[str, str]]] = []

    for task in tasks:
        fields_to_translate: dict[str, str] = {}
        if _has_english_text(task.title):
            fields_to_translate["title"] = task.title
        if _has_english_text(task.description):
            fields_to_translate["description"] = task.description
        if _has_english_text(task.feedback):
            fields_to_translate["feedback"] = task.feedback

        if not fields_to_translate:
            continue

        logger.info("Task #%d: translating fields %s", task.id, list(fields_to_translate))

        try:
            translated = await _translate_fields(fields_to_translate)
        except Exception as exc:
            logger.error("Task #%d: translation failed — %s", task.id, exc)
            continue

        changed: dict[str, str] = {}
        if "title" in translated and translated["title"] != task.title:
            changed["title"] = translated["title"]
            task.title = translated["title"]
        if "description" in translated and translated.get("description") != task.description:
            changed["description"] = translated["description"]
            task.description = translated["description"]
        if "feedback" in translated and translated.get("feedback") != task.feedback:
            changed["feedback"] = translated["feedback"]
            task.feedback = translated["feedback"]

        if changed:
            pending.append((task, changed))

    # ------------------------------------------------------------------ #
    # 3. Batch DB update — single commit for all changes
    # ------------------------------------------------------------------ #
    updated_count = len(pending)
    db_committed = False

    if pending:
        async with AsyncSessionLocal() as session:
            for task, changed in pending:
                await session.execute(
                    update(Task).where(Task.id == task.id).values(**changed)
                )
            await session.commit()
        db_committed = True
        logger.info("DB commit: %d records updated", updated_count)
    else:
        logger.info("No records require updating")

    # ------------------------------------------------------------------ #
    # 4. Notion sync — only after successful DB commit
    # ------------------------------------------------------------------ #
    notion_synced = 0
    notion_failed = 0
    notion_skipped = 0

    if db_committed:
        for task, _ in pending:
            if not task.notion_page_id:
                notion_skipped += 1
                continue
            try:
                await _sync_notion(
                    task_id=task.id,
                    notion_page_id=task.notion_page_id,
                    title=task.title,
                    description=task.description,
                    feedback=task.feedback,
                )
                notion_synced += 1
            except Exception as exc:
                logger.error("Task #%d: Notion sync error — %s", task.id, exc)
                notion_failed += 1

    # ------------------------------------------------------------------ #
    # 5. Report
    # ------------------------------------------------------------------ #
    sep = "=" * 58
    print(f"\n{sep}")
    print("  РЕЗУЛЬТАТ МІГРАЦІЇ")
    print(sep)
    print(f"  Перевірено задач            : {total}")
    print(f"  Оновлено задач              : {updated_count}")
    print(f"  Commit в БД                 : {'Виконано' if db_committed else 'Не потрібен'}")
    print(f"  Синхронізовано в Notion     : {notion_synced}")
    print(f"  Пропущено (без Notion ID)   : {notion_skipped}")
    print(f"  Помилок Notion              : {notion_failed}")
    print(sep)

    if pending:
        print("\n  Деталі оновлених задач:")
        for task, changed in pending:
            fields_str = ", ".join(changed.keys())
            print(f"    Task #{task.id:<4} — поля: {fields_str}")

    status_ok = db_committed and notion_failed == 0
    print()
    print(
        f"  Статус: {'OK — всі зміни збережені та синхронізовані з Notion' if status_ok else 'УВАГА — є помилки Notion (докладніше у лозі)'}"
    )
    print(f"{sep}\n")


if __name__ == "__main__":
    asyncio.run(main())
