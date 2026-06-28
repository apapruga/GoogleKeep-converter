from __future__ import annotations

import argparse
import base64
import glob
import hashlib
import html
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser


@dataclass
class Note:
    title: str = ""
    text_content: str = ""
    text_content_html: str = ""
    list_content: list = field(default_factory=list)
    labels: list = field(default_factory=list)
    annotations: list = field(default_factory=list)
    attachments: list = field(default_factory=list)
    created_usec: int = 0
    edited_usec: int = 0
    is_trashed: bool = False
    source_name: str = ""


def parse_note(json_path):
    """Прочитать .json выгрузки Keep в Note."""
    with open(json_path, "r", encoding="utf-8") as f:
        d = json.load(f)
    return Note(
        title=(d.get("title") or "").strip(),
        text_content=d.get("textContent") or "",
        text_content_html=d.get("textContentHtml") or "",
        list_content=d.get("listContent") or [],
        labels=d.get("labels") or [],
        annotations=d.get("annotations") or [],
        attachments=d.get("attachments") or [],
        created_usec=d.get("createdTimestampUsec") or 0,
        edited_usec=d.get("userEditedTimestampUsec") or 0,
        is_trashed=bool(d.get("isTrashed")),
        source_name=os.path.splitext(os.path.basename(json_path))[0],
    )


def xml_text_escape(text):
    """Экранирование &, <, > для текстовых XML-узлов (заголовок заметки)."""
    return html.escape(text or "", quote=False)


ALLOWED_TAGS = {"div", "p", "br", "span", "b", "i", "u", "a", "ul", "ol", "li", "strong", "em"}
SELF_CLOSING_TAGS = {"br"}
DROP_CONTENT_TAGS = {"script", "style", "head", "meta", "html", "body"}


class _Sanitizer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if self.skip_depth:
            return
        if tag in DROP_CONTENT_TAGS:
            self.skip_depth += 1
            return
        if tag in ALLOWED_TAGS:
            kept = []
            for key, value in attrs:
                if tag == "a" and key == "href" and value:
                    kept.append(f'href="{html.escape(value, quote=True)}"')
            attr_str = (" " + " ".join(kept)) if kept else ""
            if tag in SELF_CLOSING_TAGS:
                self.out.append(f"<{tag}{attr_str}/>")
            else:
                self.out.append(f"<{tag}{attr_str}>")
        # неизвестные теги: выбрасываем тег, но сохраняем внутренний текст.

    def handle_startendtag(self, tag, attrs):
        # <br/>, <img/> и т. п.
        if self.skip_depth:
            return
        if tag in DROP_CONTENT_TAGS:
            return
        if tag in ALLOWED_TAGS:
            self.handle_starttag(tag, attrs)
            if tag not in SELF_CLOSING_TAGS:
                self.out.append(f"</{tag}>")

    def handle_endtag(self, tag):
        if tag in DROP_CONTENT_TAGS and self.skip_depth:
            self.skip_depth -= 1
            return
        if self.skip_depth:
            return
        if tag in ALLOWED_TAGS and tag not in SELF_CLOSING_TAGS:
            self.out.append(f"</{tag}>")

    def handle_data(self, data):
        if self.skip_depth:
            return
        self.out.append(html.escape(data, quote=False))

    def result(self):
        return "".join(self.out)


def sanitize_html(html_text):
    """Очистить Keep-HTML до разрешённого ENML-подмножества тегов."""
    if not html_text:
        return ""
    sanitizer = _Sanitizer()
    sanitizer.feed(html_text)
    sanitizer.close()
    return sanitizer.result()


def render_text(text):
    """Чистый текст -> последовательность <div>-абзацев (ENML-совместимо)."""
    if not text:
        return ""
    parts = []
    for line in text.split("\n"):
        if line == "":
            parts.append("<div><br/></div>")
        else:
            parts.append(f"<div>{html.escape(line)}</div>")
    return "".join(parts)


def render_checklist(items):
    """listContent Keep -> <ul> с символами ☑/☐ перед текстом пункта."""
    parts = ["<ul>"]
    for item in items:
        mark = "☑" if item.get("isChecked", False) else "☐"
        text = item.get("text", "") or ""
        parts.append(f"<li>{mark} {html.escape(text)}</li>")
    parts.append("</ul>")
    return "".join(parts)


def render_labels(labels):
    """labels Keep -> блок '#тег #тег' серым в начале тела."""
    if not labels:
        return ""
    tags = " ".join("#" + (lbl.get("name", "")).strip() for lbl in labels)
    return f'<div style="color:#999">🏷 {html.escape(tags)}</div><div><br/></div>'


def render_annotations(annotations):
    """annotations Keep -> блок кликабельных ссылок в конце тела."""
    if not annotations:
        return ""
    parts = ['<div><br/></div>', '<div style="color:#999">Ссылки:</div>']
    for ann in annotations:
        url = ann.get("url", "") or ""
        title = ann.get("title", "") or url or "ссылка"
        parts.append(
            f'<div><a href="{html.escape(url, quote=True)}">{html.escape(title)}</a></div>'
        )
    return "".join(parts)


MIME_BY_EXTENSION = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
}


def _mime_for(filename, mimetype):
    if mimetype:
        return mimetype
    ext = os.path.splitext(filename)[1].lower()
    return MIME_BY_EXTENSION.get(ext, "application/octet-stream")


def media_and_resources(note, base_dir):
    """Вернуть (media_html, resources_xml) для attachments заметки."""
    media_parts = []
    resource_parts = []
    for att in note.attachments:
        fname = att.get("filePath", "") or ""
        path = os.path.join(base_dir, fname)
        if not os.path.isfile(path):
            media_parts.append(f"<div>[Вложение отсутствует: {html.escape(fname)}]</div>")
            continue
        with open(path, "rb") as fh:
            data = fh.read()
        digest = hashlib.md5(data).hexdigest()
        mime = _mime_for(fname, att.get("mimetype", ""))
        media_parts.append(f'<en-media type="{mime}" hash="{digest}"/>')
        b64 = base64.b64encode(data).decode("ascii")
        resource_parts.append(
            "<resource>"
            f'<data encoding="base64">{b64}</data>'
            f"<mime>{mime}</mime>"
            "<resource-attributes>"
            f"<file-name>{html.escape(os.path.basename(fname))}</file-name>"
            "</resource-attributes>"
            "</resource>"
        )
    return "".join(media_parts), "".join(resource_parts)


def render_body(note):
    """Собрать тело <en-note> (без медиа). Порядок: labels, content, annotations."""
    blocks = []

    labels_html = render_labels(note.labels)
    if labels_html:
        blocks.append(labels_html)

    if note.list_content:
        blocks.append(render_checklist(note.list_content))
    else:
        sanitized = sanitize_html(note.text_content_html)
        if sanitized.strip():
            blocks.append(sanitized)
        else:
            blocks.append(render_text(note.text_content))

    annotations_html = render_annotations(note.annotations)
    if annotations_html:
        blocks.append(annotations_html)

    return "".join(blocks)


def format_timestamp(usec):
    """Микросекунды (UTC) -> 'YYYYMMDDTHHMMSSZ'. Пустой/0 -> текущее время UTC."""
    if not usec:
        usec = int(datetime.now(timezone.utc).timestamp() * 1_000_000)
    dt = datetime.fromtimestamp(usec / 1_000_000, tz=timezone.utc)
    return dt.strftime("%Y%m%dT%H%M%SZ")


def main(argv=None):
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
