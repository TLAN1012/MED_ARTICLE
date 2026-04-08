#!/usr/bin/env python3
"""render_preview.py — 把 MED_ARTICLE 文章 md 渲染成自含 HTML 預覽。

用途：藍醫師推上 WordPress 前先在本機看一眼版面。

用法：
    python3 render_preview.py <article-folder>
    # 例：python3 render_preview.py articles/restless_legs_syndrome

輸出：<article-folder>/preview.html  （瀏覽器直接打開）

慣例：
- 文章主檔固定叫 index.md
- 封面圖固定叫 images/<article-name>_overview.jpg（或 images/cover.jpg）
- 找得到封面圖就放在文章標題上方當 hero
"""
import sys
from pathlib import Path
from typing import Optional

import markdown


CSS = """
:root {
  --max-w: 760px;
  --bg: #fafaf8;
  --fg: #1f2937;
  --muted: #6b7280;
  --accent: #2563eb;
  --warn-bg: #fef9e7;
  --warn-bd: #f59e0b;
  --table-bd: #e5e7eb;
  --code-bg: #f3f4f6;
}
* { box-sizing: border-box; }
html, body {
  margin: 0; padding: 0; background: var(--bg); color: var(--fg);
  font-family: -apple-system, "PingFang TC", "Noto Sans TC", "Microsoft JhengHei",
               "Helvetica Neue", sans-serif;
  font-size: 17px; line-height: 1.85; -webkit-font-smoothing: antialiased;
}
.wrap { max-width: var(--max-w); margin: 0 auto; padding: 32px 24px 96px; }
.hero { width: 100%; aspect-ratio: 16/9; object-fit: cover;
  border-radius: 12px; margin-bottom: 32px; box-shadow: 0 8px 24px rgba(0,0,0,0.08); }
h1 { font-size: 2em; line-height: 1.3; margin: 0 0 0.6em; letter-spacing: 0.02em; }
h2 { font-size: 1.45em; line-height: 1.4; margin: 2.2em 0 0.8em;
  padding-bottom: 0.3em; border-bottom: 2px solid var(--table-bd); }
h3 { font-size: 1.2em; margin: 1.8em 0 0.6em; color: #374151; }
h4 { font-size: 1.05em; margin: 1.4em 0 0.5em; color: #4b5563; }
p { margin: 0.9em 0; }
ul, ol { padding-left: 1.6em; margin: 0.9em 0; }
li { margin: 0.3em 0; }
strong { color: #111827; }
em { color: #4b5563; }
a { color: var(--accent); text-decoration: none; border-bottom: 1px solid #c7dbff; }
a:hover { background: #eef4ff; }
hr { border: none; border-top: 1px solid var(--table-bd); margin: 2.4em 0; }
blockquote {
  margin: 1.4em 0; padding: 14px 20px; background: var(--warn-bg);
  border-left: 4px solid var(--warn-bd); border-radius: 4px; color: #4b3f10;
}
blockquote p { margin: 0.4em 0; }
table { border-collapse: collapse; width: 100%; margin: 1.2em 0; font-size: 0.95em; }
th, td { border: 1px solid var(--table-bd); padding: 8px 12px; text-align: left; vertical-align: top; }
th { background: #f3f4f6; font-weight: 600; }
tr:nth-child(even) td { background: #fafafa; }
code {
  background: var(--code-bg); padding: 2px 6px; border-radius: 4px;
  font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size: 0.92em;
}
pre code { display: block; padding: 12px; overflow-x: auto; }
.preview-banner {
  background: #fffbeb; border: 1px solid #fcd34d; border-radius: 8px;
  padding: 10px 16px; margin-bottom: 24px; font-size: 14px; color: #78350f;
}
.preview-banner strong { color: #78350f; }
.disclaimer {
  margin-top: 3em; padding: 16px 20px; background: #f3f4f6;
  border-radius: 8px; font-size: 0.9em; color: var(--muted);
}
"""

HTML_TMPL = """<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — 預覽</title>
<style>{css}</style>
</head>
<body>
<div class="wrap">
  <div class="preview-banner">
    📝 <strong>本機預覽</strong> · 來源：<code>{src_rel}</code>
    · 推上 WordPress 前的最後一次校稿視圖
  </div>
  {hero}
  {body}
</div>
</body>
</html>
"""


def find_cover(article_dir: Path, slug: str) -> Optional[Path]:
    """找封面圖。優先序：精確命名 → *_overview.* → cover.* / hero.* → images/ 第一張。
    任何 0-byte 檔（之前失敗留下的占位符）一律忽略。"""
    images_dir = article_dir / "images"
    if not images_dir.is_dir():
        return None

    def alive(p: Path) -> bool:
        return p.is_file() and p.stat().st_size > 0

    # 1. 精確命名
    for ext in ("jpg", "jpeg", "png", "webp"):
        p = images_dir / f"{slug}_overview.{ext}"
        if alive(p):
            return p

    # 2. 任意 *_overview.*
    for p in sorted(images_dir.glob("*_overview.*")):
        if alive(p):
            return p

    # 3. cover.* / hero.*
    for stem in ("cover", "hero"):
        for p in sorted(images_dir.glob(f"{stem}.*")):
            if alive(p):
                return p

    # 4. images/ 第一張不是 0-byte 的圖
    for p in sorted(images_dir.iterdir()):
        if alive(p) and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
            return p

    return None


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    article_dir = Path(sys.argv[1]).resolve()
    if not article_dir.is_dir():
        sys.exit(f"❌ 不是資料夾：{article_dir}")
    md_path = article_dir / "index.md"
    if not md_path.is_file():
        sys.exit(f"❌ 找不到 {md_path}")

    slug = article_dir.name
    md_text = md_path.read_text(encoding="utf-8")

    # 抓第一行 # 標題
    title = next((l.lstrip("# ").strip() for l in md_text.splitlines() if l.startswith("# ")), slug)

    body_html = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "sane_lists"],
    )

    # 把第一個 <h1> 拿掉避免重複（hero + h1 + h1 看起來怪）
    # 不拿掉，因為 h1 本身就是文章主標，放在 hero 下方剛好

    cover = find_cover(article_dir, slug)
    if cover:
        rel = cover.relative_to(article_dir)
        hero = f'<img class="hero" src="{rel}" alt="{title} 封面圖">'
    else:
        hero = ""

    out_path = article_dir / "preview.html"
    out_path.write_text(
        HTML_TMPL.format(
            title=title,
            css=CSS,
            src_rel=md_path.relative_to(article_dir),
            hero=hero,
            body=body_html,
        ),
        encoding="utf-8",
    )
    print(f"✅ {out_path}")
    print(f"   open: file://{out_path}")


if __name__ == "__main__":
    main()
