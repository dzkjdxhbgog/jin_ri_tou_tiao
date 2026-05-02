#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
import argparse
from dataclasses import dataclass
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


CHANNEL_URL = "https://t.me/s/remote_cn"
OUTPUT_DIR = Path(__file__).resolve().parent / "采集结果"
START_INDEX = 474
ENDING_TEXT = "#远程工作 #招聘\n招聘信息均收集自网络，是否靠谱请自行判断，如有投递意愿，请访问原文联系。"
BEIJING_TIME = ZoneInfo("Asia/Shanghai")


@dataclass
class Message:
    post_id: int
    datetime: str
    text: str


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "br":
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"p", "div"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        raw = "".join(self.parts)
        lines = [line.strip() for line in raw.splitlines()]
        normalized: list[str] = []
        blank = False
        for line in lines:
            if not line:
                if not blank:
                    normalized.append("")
                blank = True
                continue
            normalized.append(line)
            blank = False
        return "\n".join(normalized).strip()


def fetch_html(before: int | None = None) -> str:
    url = CHANNEL_URL if before is None else f"{CHANNEL_URL}?before={before}"
    req = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            )
        },
    )
    with urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def html_to_text(fragment: str) -> str:
    parser = TextExtractor()
    parser.feed(fragment)
    return parser.text()


def extract_messages(html: str) -> list[Message]:
    starts = list(re.finditer(r'data-post="remote_cn/(\d+)"', html))
    messages: list[Message] = []
    for index, match in enumerate(starts):
        post_id = int(match.group(1))
        end = starts[index + 1].start() if index + 1 < len(starts) else len(html)
        block = html[match.start() : end]
        text_match = re.search(
            r'<div class="tgme_widget_message_text js-message_text"[^>]*>(.*?)</div>',
            block,
            flags=re.S,
        )
        if not text_match:
            continue
        datetime_match = re.search(r'<time datetime="([^"]+)"', block)
        messages.append(
            Message(
                post_id=post_id,
                datetime=datetime_match.group(1) if datetime_match else "",
                text=html_to_text(text_match.group(1)),
            )
        )
    return messages


def message_date(message: Message) -> date | None:
    if not message.datetime:
        return None
    return datetime.fromisoformat(message.datetime).astimezone(BEIJING_TIME).date()


def is_job_message(text: str) -> bool:
    stripped = text.strip()
    first_line = next((line.strip() for line in stripped.splitlines() if line.strip()), "")

    reject_terms = (
        "[广告]",
        "欢迎关注",
        "发现一个新的远程工作TG频道",
        "远程工作AI情报站",
    )
    if any(term in stripped for term in reject_terms):
        return False
    if first_line.startswith("[远程工作机会]"):
        return False
    if "mp.weixin.qq.com" in stripped:
        return False
    if "来源:" not in stripped or "摘要:" not in stripped:
        return False
    return bool(re.search(r"https?://", stripped))


def clean_message(text: str) -> str:
    banned_exact = {
        "招聘信息均收集自网络，是否靠谱请自行判断，如有投递意愿，请访问原文联系。",
    }
    cleaned: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            cleaned.append("")
            continue
        if line in banned_exact:
            continue
        if "#远程工作" in line or "#招聘" in line:
            continue
        if line.startswith("查看更多远程工作机会"):
            continue
        if "remote-china.com" in line:
            continue
        cleaned.append(line)

    while cleaned and not cleaned[0]:
        cleaned.pop(0)
    while cleaned and not cleaned[-1]:
        cleaned.pop()

    compact: list[str] = []
    blank = False
    for line in cleaned:
        if not line:
            if not blank:
                compact.append("")
            blank = True
            continue
        compact.append(line)
        blank = False
    return "\n".join(compact).strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect remote_cn jobs by Beijing date.")
    parser.add_argument(
        "--date",
        help="北京时间日期，格式 YYYY-MM-DD；不填则使用今天的北京时间日期。",
    )
    return parser.parse_args()


def collect_messages(target_date: date) -> list[Message]:
    before: int | None = None
    collected: list[Message] = []
    seen: set[int] = set()

    for _ in range(20):
        html = fetch_html(before)
        messages = [message for message in extract_messages(html) if message.post_id not in seen]
        if not messages:
            break

        seen.update(message.post_id for message in messages)
        dated_messages = [(message, message_date(message)) for message in messages]
        collected.extend(message for message, msg_date in dated_messages if msg_date == target_date)

        dates = [msg_date for _, msg_date in dated_messages if msg_date is not None]
        if dates and min(dates) < target_date:
            break

        before = min(message.post_id for message in messages)

    return sorted(collected, key=lambda message: message.post_id)


def main() -> int:
    args = parse_args()
    target_date = date.fromisoformat(args.date) if args.date else datetime.now(BEIJING_TIME).date()
    messages = collect_messages(target_date)
    jobs = [clean_message(message.text) for message in messages if is_job_message(message.text)]
    jobs = [job for job in jobs if job]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    date_name = target_date.isoformat()
    output_path = OUTPUT_DIR / f"{date_name}.md"
    numbered_jobs = [f"{START_INDEX + index}.\n{job}" for index, job in enumerate(jobs)]
    if numbered_jobs:
        numbered_jobs[-1] = f"{numbered_jobs[-1]}\n\n{ENDING_TEXT}"
    output_path.write_text("\n\n---\n\n".join(numbered_jobs) + ("\n" if jobs else ""), encoding="utf-8")

    print(f"saved={output_path}")
    print(f"messages={len(messages)} jobs={len(jobs)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
