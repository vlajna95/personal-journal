"""Export functionality for Personal Journal.

Supports exporting diary entries and notes as:
  - One Pelican-formatted Markdown post per entry/note
  - One Pelican post per calendar week
  - One Pelican post per calendar month
  - All content merged into a single Markdown document

When a custom template file path is supplied, all Pelican exports use that
template instead of the built-in header.  Available placeholders:
  {title} {date} {entry_date} {export_time} {modified} {tags} {summary}
  {description} {series} {series_index} {trans_id} {lang} {content}
  {diary_name} {year} {month} {day}
"""

import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from cryptography.fernet import Fernet

import database


# ---------------------------------------------------------------------------
# Locale loading
# ---------------------------------------------------------------------------

_locale_cache: dict[str, dict[str, str]] = {}


def _load_locale(lang: str) -> dict[str, str]:
    if lang in _locale_cache:
        return _locale_cache[lang]
    locale_dir = Path(__file__).parent / "locales"
    for lng_file in sorted(locale_dir.glob("*.lng")):
        data: dict[str, str] = {}
        try:
            for line in lng_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                data[k.strip()] = v.strip()
        except Exception:
            continue
        if data.get("lang.code") == lang:
            _locale_cache[lang] = data
            return data
    if lang != "en":
        return _load_locale("en")
    return {}


def _locale_month(lang: str, month: int) -> str:
    return _load_locale(lang).get(f"date.month.{month}", str(month))


def _notes_label(lang: str) -> str:
    return _load_locale(lang).get("tab.notes", "Notes")


# ---------------------------------------------------------------------------
# Localized date title formatting
# ---------------------------------------------------------------------------

def _format_month_title(lang: str, year: int, month: int) -> str:
    m = _locale_month(lang, month)
    fmt = _load_locale(lang).get("export.fmt_month_title", "{month} {year}")
    return fmt.format(month=m, month_lc=m.lower(), year=year)


def _format_week_title(lang: str, first_dt: datetime, last_dt: datetime) -> str:
    loc = _load_locale(lang)
    d1 = first_dt.day
    d2 = last_dt.day
    y1 = first_dt.year
    y2 = last_dt.year
    m1 = _locale_month(lang, first_dt.month)
    m2 = _locale_month(lang, last_dt.month)

    if y1 != y2:
        fmt = loc.get("export.fmt_week_cross_year", "{d1} {m1} {y1}–{d2} {m2} {y2}")
        return fmt.format(d1=d1, m1=m1, m1_lc=m1.lower(), y1=y1,
                          d2=d2, m2=m2, m2_lc=m2.lower(), y2=y2)
    elif first_dt.month != last_dt.month:
        fmt = loc.get("export.fmt_week_cross", "{d1} {m1}–{d2} {m2} {year}")
        return fmt.format(d1=d1, m1=m1, m1_lc=m1.lower(),
                          d2=d2, m2=m2, m2_lc=m2.lower(), year=y1)
    else:
        fmt = loc.get("export.fmt_week_same", "{d1}–{d2} {month} {year}")
        return fmt.format(d1=d1, d2=d2, month=m1, month_lc=m1.lower(), year=y1)


# ---------------------------------------------------------------------------
# Content helpers
# ---------------------------------------------------------------------------

def _slugify(text: str, max_len: int = 50) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")[:max_len]


def _extract_title_and_summary(content: str) -> tuple:
    """Return (title_or_None, summary_str) extracted from Markdown content."""
    lines = content.splitlines()
    title = None
    start_idx = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#"):
            title = re.sub(r"^#+\s*", "", stripped)
            start_idx = i + 1
            break
    summary_parts: list[str] = []
    in_para = False
    for line in lines[start_idx:]:
        stripped = line.strip()
        if not stripped:
            if in_para:
                break
            continue
        if stripped.startswith("#"):
            if in_para:
                break
            continue
        in_para = True
        summary_parts.append(stripped)
    summary = " ".join(summary_parts)
    if len(summary) > 300:
        cut = summary[:300].rsplit(" ", 1)
        summary = (cut[0] if len(cut) > 1 else summary[:300]) + "..."
    return title, summary


def _week_key(iso_date: str) -> tuple:
    dt = datetime.strptime(iso_date, "%Y-%m-%d")
    cal = dt.isocalendar()
    return cal[0], cal[1]


def _month_key(iso_date: str) -> tuple:
    dt = datetime.strptime(iso_date, "%Y-%m-%d")
    return dt.year, dt.month


# ---------------------------------------------------------------------------
# Pelican header (built-in default format)
# ---------------------------------------------------------------------------

def _pelican_header(*, title: str, entry_date: str, export_time: str,
                    tags: str, summary: str, lang: str, series: str,
                    series_index: int, trans_id: str) -> str:
    modified = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"Title: {title}",
        f"Date: {entry_date} {export_time}",
    ]
    if tags.strip():
        lines.append(f"Tags: {tags.strip()}")
    lines += [f"Summary: {summary}", f"Description: {summary}"]
    if series.strip():
        lines.append(f"Series: {series.strip()}")
        lines.append(f"Series_index: {series_index}")
    lines += [
        f"Modified: {modified}",
        f"Trans_id: {trans_id}",
        f"Lang: {lang}",
        "", "", "[TOC]", "", "-----", "", "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Default template
# ---------------------------------------------------------------------------

DEFAULT_TEMPLATE = """\
Title: {title}
Date: {date}
Tags: {tags}
Summary: {summary}
Description: {description}
Series: {series}
Series_index: {series_index}
Modified: {modified}
Trans_id: {trans_id}
Lang: {lang}


[TOC]

-----

{content}
"""

# ---------------------------------------------------------------------------
# Custom template support
# ---------------------------------------------------------------------------

class _SafeMap(dict):
    """dict subclass that returns the key placeholder for missing keys."""
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _make_ctx(*, title: str, entry_date: str, export_time: str,
              tags: str, summary: str, lang: str, series: str,
              series_index: int, trans_id: str, content: str,
              diary_name: str = "") -> dict:
    modified = datetime.now().strftime("%Y-%m-%d %H:%M")
    dt = datetime.strptime(entry_date, "%Y-%m-%d")
    return {
        "title": title,
        "entry_date": entry_date,
        "export_time": export_time,
        "date": f"{entry_date} {export_time}",
        "modified": modified,
        "tags": tags,
        "summary": summary,
        "description": summary,
        "series": series,
        "series_index": series_index,
        "trans_id": trans_id,
        "lang": lang,
        "content": content,
        "diary_name": diary_name,
        "year": dt.year,
        "month": dt.month,
        "day": dt.day,
    }


def _apply_template(template: str, ctx: dict) -> str:
    """Render a custom template string using ctx variables.

    If the template contains {content}, that placeholder is filled.
    Otherwise the content value is appended after the rendered template.
    """
    result = template.format_map(_SafeMap(ctx))
    if "{content}" not in template:
        result += ctx.get("content", "")
    return result


def _render(template: str | None, ctx: dict) -> str:
    """Return rendered output: custom template if given, else built-in header + content."""
    if template:
        return _apply_template(template, ctx)
    header = _pelican_header(
        title=ctx["title"],
        entry_date=ctx["entry_date"],
        export_time=ctx["export_time"],
        tags=ctx["tags"],
        summary=ctx["summary"],
        lang=ctx["lang"],
        series=ctx["series"],
        series_index=ctx["series_index"],
        trans_id=ctx["trans_id"],
    )
    return header + ctx["content"]


# ---------------------------------------------------------------------------
# Diary helpers
# ---------------------------------------------------------------------------

def _get_diary_list(fernet: Fernet, diary_id) -> list:
    """Return [{id, name}]. If diary_id is None, return all diaries."""
    all_diaries = database.get_diaries(fernet)
    if diary_id is None:
        return all_diaries
    for d in all_diaries:
        if d["id"] == diary_id:
            return [d]
    return [{"id": diary_id, "name": f"diary-{diary_id}"}]


# ---------------------------------------------------------------------------
# Diary exports
# ---------------------------------------------------------------------------

def export_diary_per_entry(fernet: Fernet, output_dir: Path,
                           lang: str, tags: str, series: str,
                           diary_id=1, template: str | None = None) -> int:
    """Export each diary entry as a separate Pelican .md file."""
    diaries = _get_diary_list(fernet, diary_id)
    multi = len(diaries) > 1
    output_dir.mkdir(parents=True, exist_ok=True)
    export_time = datetime.now().strftime("%H:%M")
    total = 0
    for diary in diaries:
        d_id = diary["id"]
        d_name = diary["name"]
        d_slug = _slugify(d_name)
        effective_series = series.strip() or d_name
        entries = database.get_all_diary_entries(fernet, d_id)
        for idx, entry in enumerate(entries, 1):
            d = entry["entry_date"]
            entry_title, entry_summary = _extract_title_and_summary(entry["content"])
            if entry_title is None:
                entry_title = f"{d_name} – {d}"
            trans_id = f"{_slugify(effective_series)}__{_slugify(entry_title)}"
            ctx = _make_ctx(
                title=entry_title,
                entry_date=d,
                export_time=export_time,
                tags=tags,
                summary=entry_summary or f"{d_name} – {d}",
                lang=lang,
                series=effective_series,
                series_index=idx,
                trans_id=trans_id,
                content=entry["content"],
                diary_name=d_name,
            )
            fname = f"{d_slug}-{d}.md" if multi else f"{d}.md"
            (output_dir / fname).write_text(_render(template, ctx), encoding="utf-8")
            total += 1
    return total


def export_diary_per_week(fernet: Fernet, output_dir: Path,
                          lang: str, tags: str, series: str,
                          diary_id=1, template: str | None = None) -> int:
    """Export diary entries grouped by ISO week as Pelican .md files."""
    diaries = _get_diary_list(fernet, diary_id)
    multi = len(diaries) > 1
    output_dir.mkdir(parents=True, exist_ok=True)
    export_time = datetime.now().strftime("%H:%M")
    total = 0
    for diary in diaries:
        d_id = diary["id"]
        d_name = diary["name"]
        d_slug = _slugify(d_name)
        effective_series = series.strip() or d_name
        entries = database.get_all_diary_entries(fernet, d_id)
        groups: dict = defaultdict(list)
        for entry in entries:
            groups[_week_key(entry["entry_date"])].append(entry)
        for idx, (yw, week_entries) in enumerate(sorted(groups.items()), 1):
            year, week = yw
            dates_in_week = sorted(e["entry_date"] for e in week_entries)
            first_dt = datetime.strptime(dates_in_week[0], "%Y-%m-%d")
            last_dt = datetime.strptime(dates_in_week[-1], "%Y-%m-%d")
            date_range = _format_week_title(lang, first_dt, last_dt)
            week_title = f"{d_name} – {date_range}"
            combined = "\n\n---\n\n".join(
                f"### {e['entry_date']}\n\n{e['content']}" for e in week_entries
            )
            ctx = _make_ctx(
                title=week_title,
                entry_date=dates_in_week[0],
                export_time=export_time,
                tags=tags,
                summary=f"{d_name} – {date_range}",
                lang=lang,
                series=effective_series,
                series_index=idx,
                trans_id=f"{_slugify(effective_series)}__{_slugify(week_title)}",
                content=combined,
                diary_name=d_name,
            )
            fname = f"{d_slug}-{year}-W{week:02d}.md" if multi else f"{year}-W{week:02d}.md"
            (output_dir / fname).write_text(_render(template, ctx), encoding="utf-8")
            total += 1
    return total


def export_diary_per_month(fernet: Fernet, output_dir: Path,
                           lang: str, tags: str, series: str,
                           diary_id=1, template: str | None = None) -> int:
    """Export diary entries grouped by month as Pelican .md files."""
    diaries = _get_diary_list(fernet, diary_id)
    multi = len(diaries) > 1
    output_dir.mkdir(parents=True, exist_ok=True)
    export_time = datetime.now().strftime("%H:%M")
    total = 0
    for diary in diaries:
        d_id = diary["id"]
        d_name = diary["name"]
        d_slug = _slugify(d_name)
        effective_series = series.strip() or d_name
        entries = database.get_all_diary_entries(fernet, d_id)
        groups: dict = defaultdict(list)
        for entry in entries:
            groups[_month_key(entry["entry_date"])].append(entry)
        for idx, (ym, month_entries) in enumerate(sorted(groups.items()), 1):
            year, month = ym
            date_range = _format_month_title(lang, year, month)
            month_title = f"{d_name} – {date_range}"
            combined = "\n\n---\n\n".join(
                f"### {e['entry_date']}\n\n{e['content']}" for e in month_entries
            )
            first_date = sorted(e["entry_date"] for e in month_entries)[0]
            ctx = _make_ctx(
                title=month_title,
                entry_date=first_date,
                export_time=export_time,
                tags=tags,
                summary=f"{d_name} – {date_range}",
                lang=lang,
                series=effective_series,
                series_index=idx,
                trans_id=f"{_slugify(effective_series)}__{_slugify(month_title)}",
                content=combined,
                diary_name=d_name,
            )
            fname = f"{d_slug}-{year}-{month:02d}.md" if multi else f"{year}-{month:02d}.md"
            (output_dir / fname).write_text(_render(template, ctx), encoding="utf-8")
            total += 1
    return total


def export_diary_single_markdown(fernet: Fernet, output_path: Path, diary_id=1) -> int:
    """Export all diary entries to a single Markdown file (no Pelican header)."""
    diaries = _get_diary_list(fernet, diary_id)
    all_entries: list = []
    for diary in diaries:
        for e in database.get_all_diary_entries(fernet, diary["id"]):
            all_entries.append((diary["name"], e))
    all_entries.sort(key=lambda x: x[1]["entry_date"])
    multi = len(diaries) > 1
    parts = []
    for d_name, e in all_entries:
        heading = f"## {e['entry_date']} ({d_name})" if multi else f"## {e['entry_date']}"
        parts.append(f"{heading}\n\n{e['content']}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n\n---\n\n".join(parts), encoding="utf-8")
    return len(all_entries)


# ---------------------------------------------------------------------------
# Notes exports
# ---------------------------------------------------------------------------

def export_notes_per_note(fernet: Fernet, output_dir: Path,
                          lang: str, tags: str, series: str,
                          template: str | None = None) -> int:
    """Export each note as a separate Pelican .md file."""
    notes = database.get_all_notes(fernet)
    output_dir.mkdir(parents=True, exist_ok=True)
    export_time = datetime.now().strftime("%H:%M")
    notes_label = _notes_label(lang)
    effective_series = series.strip() or notes_label
    for idx, note in enumerate(notes, 1):
        base_slug = _slugify(note["subject"])
        _, content_summary = _extract_title_and_summary(note["content"])
        ctx = _make_ctx(
            title=note["subject"],
            entry_date=note["note_date"],
            export_time=export_time,
            tags=tags,
            summary=content_summary or note["subject"],
            lang=lang,
            series=effective_series,
            series_index=idx,
            trans_id=f"{_slugify(effective_series)}__{base_slug}-{note['id']}",
            content=note["content"],
            diary_name=notes_label,
        )
        filename = f"{note['note_date']}-{base_slug}-{note['id']}.md"
        (output_dir / filename).write_text(_render(template, ctx), encoding="utf-8")
    return len(notes)


def export_notes_per_week(fernet: Fernet, output_dir: Path,
                          lang: str, tags: str, series: str,
                          template: str | None = None) -> int:
    """Export notes grouped by ISO week as Pelican .md files."""
    notes = database.get_all_notes(fernet)
    output_dir.mkdir(parents=True, exist_ok=True)
    export_time = datetime.now().strftime("%H:%M")
    notes_label = _notes_label(lang)
    effective_series = series.strip() or notes_label
    groups: dict = defaultdict(list)
    for note in notes:
        groups[_week_key(note["note_date"])].append(note)
    for idx, (yw, week_notes) in enumerate(sorted(groups.items()), 1):
        year, week = yw
        dates_in_week = sorted(n["note_date"] for n in week_notes)
        first_dt = datetime.strptime(dates_in_week[0], "%Y-%m-%d")
        last_dt = datetime.strptime(dates_in_week[-1], "%Y-%m-%d")
        date_range = _format_week_title(lang, first_dt, last_dt)
        week_title = f"{notes_label} – {date_range}"
        combined = "\n\n---\n\n".join(
            f"### {n['subject']} ({n['note_date']})\n\n{n['content']}" for n in week_notes
        )
        ctx = _make_ctx(
            title=week_title,
            entry_date=dates_in_week[0],
            export_time=export_time,
            tags=tags,
            summary=f"{notes_label} – {date_range}",
            lang=lang,
            series=effective_series,
            series_index=idx,
            trans_id=f"{_slugify(effective_series)}__{_slugify(week_title)}",
            content=combined,
            diary_name=notes_label,
        )
        (output_dir / f"{year}-W{week:02d}.md").write_text(_render(template, ctx), encoding="utf-8")
    return len(groups)


def export_notes_per_month(fernet: Fernet, output_dir: Path,
                           lang: str, tags: str, series: str,
                           template: str | None = None) -> int:
    """Export notes grouped by month as Pelican .md files."""
    notes = database.get_all_notes(fernet)
    output_dir.mkdir(parents=True, exist_ok=True)
    export_time = datetime.now().strftime("%H:%M")
    notes_label = _notes_label(lang)
    effective_series = series.strip() or notes_label
    groups: dict = defaultdict(list)
    for note in notes:
        groups[_month_key(note["note_date"])].append(note)
    for idx, (ym, month_notes) in enumerate(sorted(groups.items()), 1):
        year, month = ym
        date_range = _format_month_title(lang, year, month)
        month_title = f"{notes_label} – {date_range}"
        combined = "\n\n---\n\n".join(
            f"### {n['subject']} ({n['note_date']})\n\n{n['content']}" for n in month_notes
        )
        first_date = sorted(n["note_date"] for n in month_notes)[0]
        ctx = _make_ctx(
            title=month_title,
            entry_date=first_date,
            export_time=export_time,
            tags=tags,
            summary=f"{notes_label} – {date_range}",
            lang=lang,
            series=effective_series,
            series_index=idx,
            trans_id=f"{_slugify(effective_series)}__{_slugify(month_title)}",
            content=combined,
            diary_name=notes_label,
        )
        (output_dir / f"{year}-{month:02d}.md").write_text(_render(template, ctx), encoding="utf-8")
    return len(groups)


def export_notes_single_markdown(fernet: Fernet, output_path: Path) -> int:
    """Export all notes to a single Markdown file grouped by date."""
    notes = database.get_all_notes(fernet)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    parts: list[str] = []
    current_date = None
    for note in notes:
        if note["note_date"] != current_date:
            current_date = note["note_date"]
            parts.append(f"# {current_date}")
        parts.append(f"## {note['subject']}\n\n{note['content']}")
    output_path.write_text("\n\n".join(parts), encoding="utf-8")
    return len(notes)
