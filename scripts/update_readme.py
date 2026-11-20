"""Refresh the "Latest from Prompt at Work" list in README.md from Sanity.

Reads the newest published blog posts from the public Sanity dataset and
rewrites the lines between the LATEST_WRITING markers. Everything else in
the README is left untouched.

Usage:
    python scripts/update_readme.py                      # read live from Sanity
    python scripts/update_readme.py --snapshot posts.json
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

PROJECT_ID = "ck8wyssm"
DATASET = "production"
API_VERSION = "v2024-01-01"
BLOG_BASE = "https://promptatwork.com/blog"  # confirm the real blog route on the site
POST_COUNT = 5

README = Path(__file__).resolve().parent.parent / "README.md"
START, END = "<!-- LATEST_WRITING:START -->", "<!-- LATEST_WRITING:END -->"

QUERY = """{
  "total": count(*[_type=="blog" && !(_id in path("drafts.**"))]),
  "posts": *[_type=="blog" && !(_id in path("drafts.**")) && defined(slug.current)]
    | order(publishedAt desc)[0...$n]{title, "slug": slug.current, publishedAt, category}
}"""


def fetch_live() -> dict:
    params = {"query": QUERY, "$n": str(POST_COUNT)}
    url = (
        f"https://{PROJECT_ID}.apicdn.sanity.io/{API_VERSION}/data/query/{DATASET}?"
        + urllib.parse.urlencode(params)
    )
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.load(response)["result"]


def format_date(value: str | None) -> str:
    if not value:
        return ""
    return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%d %b %Y").lstrip("0")


def build_block(data: dict) -> str:
    lines = []
    for post in data["posts"]:
        meta = " · ".join(x for x in (post.get("category"), format_date(post.get("publishedAt"))) if x)
        lines.append(f"- [{post['title']}]({BLOG_BASE}/{post['slug']}) <sub>{meta}</sub>")
    lines.append("")
    lines.append(f"[All {data['total']} posts on promptatwork.com]({BLOG_BASE})")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path)
    args = parser.parse_args()

    data = json.loads(args.snapshot.read_text(encoding="utf-8")) if args.snapshot else fetch_live()
    text = README.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not pattern.search(text):
        raise SystemExit("README is missing the LATEST_WRITING markers")
    updated = pattern.sub(lambda _: f"{START}\n{build_block(data)}\n{END}", text)
    README.write_text(updated, encoding="utf-8")
    print(f"Listed {len(data['posts'])} of {data['total']} posts.")


if __name__ == "__main__":
    main()
