#!/usr/bin/env python3
"""
图片下载脚本
读取每个候选选题的 images/image_candidates.md，
提取图片 URL，下载保存到对应 images/ 目录。

用法：
  python download_images.py                  # 下载今天所有候选的图片
  python download_images.py 2026-04-29       # 指定日期
  python download_images.py 2026-04-29 1034_父亲去世银行催债  # 指定单个选题
"""

from __future__ import annotations
import re
import sys
import time
import urllib.request
import ssl
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

WORKSPACE = Path(__file__).resolve().parent.parent
CANDIDATES_DIR = WORKSPACE / "candidates"
BEIJING_TZ = ZoneInfo("Asia/Shanghai")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
}

# 各平台 Referer
REFERER_MAP = {
    "sinaimg.cn": "https://finance.sina.com.cn/",
    "sina.cn": "https://finance.sina.com.cn/",
    "thepaper.cn": "https://www.thepaper.cn/",
    "guancha.cn": "https://www.guancha.cn/",
    "nbd.com.cn": "https://www.nbd.com.cn/",
    "qq.com": "https://news.qq.com/",
    "163.com": "https://www.163.com/",
}


def get_referer(url: str) -> str:
    for domain, ref in REFERER_MAP.items():
        if domain in url:
            return ref
    return "https://www.baidu.com/"


def download_image(url: str, save_path: Path, max_retries: int = 3) -> bool:
    headers = {**HEADERS, "Referer": get_referer(url)}
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
                data = resp.read()
            if len(data) < 1000:
                print(f"  ⚠️  文件太小({len(data)}B)，可能是错误页面，跳过")
                return False
            save_path.write_bytes(data)
            print(f"  ✅ 已保存 {save_path.name} ({len(data)//1024}KB)")
            return True
        except Exception as e:
            print(f"  ❌ 第{attempt}次下载失败: {e}")
            if attempt < max_retries:
                time.sleep(2)
    return False


def extract_urls_from_md(md_path: Path) -> list[tuple[str, str]]:
    """从 image_candidates.md 提取 (文件名, URL) 列表"""
    text = md_path.read_text(encoding="utf-8")
    results = []

    # 格式1: - `filename.ext`（待截）... 来源页面：URL
    # 格式2: - 原图链接：URL
    lines = text.splitlines()
    current_filename = None

    for line in lines:
        # 检测文件名行
        fn_match = re.search(r'`([\w\-]+\.(png|jpg|jpeg|webp))`', line)
        if fn_match:
            current_filename = fn_match.group(1)

        # 检测 URL 行（原图链接 或 来源页面 的直接图片URL）
        url_match = re.search(r'原图链接[：:]\s*(https?://\S+)', line)
        if url_match and current_filename:
            # 仅当 URL 直接指向图片时才下载
            url = url_match.group(1).strip()
            if any(url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
                results.append((current_filename, url))
                current_filename = None

    return results


def process_topic_folder(topic_dir: Path) -> int:
    """处理单个选题文件夹，返回成功下载数量"""
    md_path = topic_dir / "images" / "image_candidates.md"
    if not md_path.exists():
        print(f"  跳过（没有 image_candidates.md）")
        return 0

    url_pairs = extract_urls_from_md(md_path)
    if not url_pairs:
        print(f"  没有找到直接图片URL（需要截图的跳过）")
        return 0

    images_dir = topic_dir / "images"
    count = 0
    for filename, url in url_pairs:
        save_path = images_dir / filename
        if save_path.exists() and save_path.stat().st_size > 1000:
            print(f"  ⏭️  已存在 {filename}，跳过")
            count += 1
            continue
        print(f"  ⬇️  下载 {filename}")
        print(f"      URL: {url}")
        if download_image(url, save_path):
            count += 1
        time.sleep(0.5)

    return count


def main():
    args = sys.argv[1:]

    # 确定日期
    if args:
        date_str = args[0]
    else:
        date_str = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")

    date_dir = CANDIDATES_DIR / date_str
    if not date_dir.exists():
        print(f"❌ 日期目录不存在: {date_dir}")
        sys.exit(1)

    # 确定要处理的选题
    if len(args) >= 2:
        topic_dirs = [date_dir / args[1]]
    else:
        topic_dirs = [d for d in sorted(date_dir.iterdir()) if d.is_dir() and not d.name.startswith('.')]

    print(f"\n📅 日期: {date_str}  共 {len(topic_dirs)} 个选题\n")

    total_ok = 0
    for topic_dir in topic_dirs:
        print(f"📂 {topic_dir.name}")
        total_ok += process_topic_folder(topic_dir)
        print()

    print(f"✅ 完成，成功下载 {total_ok} 张图片")


if __name__ == "__main__":
    main()
