"""Systematic Tier A comparable verification with web search helpers.

Workflow:
  1. queue   — list rows needing review; workbook shows direct links (company site, saved
               citations) plus Google queries to *find* a financing source URL
  2. step    — walk one row at a time (paste the article/PR/SEC page URL, not google.com/search)
  3. apply   — merge comp_review_findings.csv into comparables.csv
  4. searches — print Google search URLs for a case or row

Example:
  python -m pipeline.tier_a.comp_web_review queue
  python -m pipeline.tier_a.comp_web_review step --case-id theromics_ri
  # edit data/ri/tier_a/comp_review_findings.csv OR use step prompts
  python -m pipeline.tier_a.comp_web_review apply
  npm run tier:a:build
"""

from __future__ import annotations

import argparse
import csv
import re
import urllib.parse
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from pipeline.tier_a.comp_financing import (
    default_anchor_type,
    discovery_search_urls,
    inferred_financing_prompt,
    value_source_prompt,
    workbook_intro,
)
from pipeline.tier_a.comp_link_resolve import (
    LINK_CACHE_CSV,
    links_for_queue_row,
    load_link_cache,
    write_link_cache,
)
from pipeline.tier_a.io import (
    comparables_by_case,
    load_comparables,
    load_registry,
    registry_by_case,
    write_comparables,
)
from pipeline.tier_a.paths import TIER_A_ROOT

QUEUE_CSV = TIER_A_ROOT / "comp_review_queue.csv"
FINDINGS_CSV = TIER_A_ROOT / "comp_review_findings.csv"
QUEUE_MD = TIER_A_ROOT / "comp_review_queue.md"

FINDINGS_FIELDS = [
    "case_id",
    "precedent_rank",
    "precedent_name",
    "action",  # verify | skip | replace | note
    "validation_status",
    "value_anchor_usd",
    "value_anchor_type",
    "value_source_url",
    "total_raised_usd_est",
    "last_round_usd_est",
    "inferred_financing",
    "precedent_notes",
    "reviewer",
    "reviewed_at",
    "search_notes",
]

QUEUE_FIELDS = [
    "queue_index",
    "case_id",
    "title_clean",
    "precedent_rank",
    "precedent_name",
    "validation_status",
    "value_anchor_usd",
    "value_source_url",
    "needs_review",
    "review_reason",
    "precedent_url",
    "primary_link_1",
    "primary_link_2",
    "primary_link_3",
    "search_vc_rounds",
    "search_total_raised",
    "search_press_vc",
    "search_acquisition",
    "search_market_cap",
]


def _needs_review(row: dict[str, str]) -> tuple[bool, str]:
    status = (row.get("validation_status") or "").lower()
    if status == "verified":
        url = (row.get("value_source_url") or "").strip()
        anchor = (row.get("value_anchor_usd") or "").strip()
        if url and anchor:
            return False, "already_verified"
        return True, "verified_missing_anchor_or_url"
    if status in {"suggested", "estimated", ""}:
        return True, f"status_{status or 'blank'}"
    return True, f"status_{status}"


def _google_url(query: str) -> str:
    return "https://www.google.com/search?q=" + urllib.parse.quote(query)


def _is_discovery_url(url: str) -> bool:
    """True when URL is a search engine results page, not a primary source."""
    lower = (url or "").strip().lower()
    return any(
        token in lower
        for token in (
            "google.com/search",
            "bing.com/search",
            "duckduckgo.com/?q=",
            "search.yahoo.com/search",
        )
    )


def _search_queries(case_title: str, comp_name: str) -> dict[str, str]:
    """Optional Google discovery URLs (CSV only); primary links are in the markdown workbook."""
    return discovery_search_urls(comp_name, google_url=_google_url)


@dataclass(frozen=True)
class QueueRow:
    index: int
    case_id: str
    title_clean: str
    comparable: dict[str, str]
    reason: str


def build_queue(*, case_id: str | None = None, include_verified: bool = False) -> list[QueueRow]:
    registry = registry_by_case(load_registry(active_only=True))
    comps = comparables_by_case()
    out: list[QueueRow] = []
    index = 0
    for cid in sorted(comps.keys()):
        if case_id and cid != case_id:
            continue
        if cid not in registry:
            continue
        title = registry[cid].get("title_clean") or cid
        for comp in comps[cid]:
            needs, reason = _needs_review(comp)
            if not needs and not include_verified:
                continue
            index += 1
            out.append(
                QueueRow(
                    index=index,
                    case_id=cid,
                    title_clean=title,
                    comparable=comp,
                    reason=reason,
                )
            )
    return out


def write_queue_files(rows: list[QueueRow], *, fetch: bool = False) -> None:
    TIER_A_ROOT.mkdir(parents=True, exist_ok=True)
    cache = load_link_cache()
    csv_rows: list[dict[str, str]] = []
    md_lines = [
        "# Tier A comparable web review queue",
        "",
        f"Generated {date.today().isoformat()}. Work top-to-bottom; record outcomes in "
        f"`comp_review_findings.csv`, then run `python -m pipeline.tier_a.comp_web_review apply`.",
        "",
        workbook_intro(),
        "",
        "Each row lists **primary-source URLs** (round PRs, Crunchbase, SEC, program pages). "
        "Pick the URL that documents the **VC staging anchor** (`total_raised`, `series_*`, `last_round`).",
        "",
    ]
    if fetch:
        md_lines.append(
            f"_Resolved via web fetch; cache: `{LINK_CACHE_CSV.name}`._"
        )
    else:
        md_lines.append(
            "_To refresh web-resolved links: "
            "`npm run tier:a:comps:queue -- --fetch`._"
        )
    md_lines.append("")

    for item in rows:
        comp = item.comparable
        rank = comp.get("precedent_rank", "")
        name = comp.get("precedent_name", "")
        searches = _search_queries(item.title_clean, name)
        links = links_for_queue_row(
            comp, case_id=item.case_id, cache=cache, fetch=fetch
        )
        if fetch and cache.get((item.case_id, rank)):
            write_link_cache(cache, merge=True)
        csv_rows.append(
            {
                "queue_index": str(item.index),
                "case_id": item.case_id,
                "title_clean": item.title_clean,
                "precedent_rank": rank,
                "precedent_name": name,
                "validation_status": comp.get("validation_status", ""),
                "value_anchor_usd": comp.get("value_anchor_usd", ""),
                "value_source_url": comp.get("value_source_url", ""),
                "needs_review": "true",
                "review_reason": item.reason,
                "precedent_url": comp.get("precedent_url", ""),
                "primary_link_1": links[0][1] if len(links) > 0 else "",
                "primary_link_2": links[1][1] if len(links) > 1 else "",
                "primary_link_3": links[2][1] if len(links) > 2 else "",
                **searches,
            }
        )
        md_lines.extend(
            [
                f"## {item.index}. {item.case_id} — rank {rank}: {name}",
                "",
                f"**Program:** {item.title_clean}  ",
                f"**Reason:** {item.reason}  ",
                f"**Current status:** {comp.get('validation_status', '')}  ",
                f"**Anchor:** {comp.get('value_anchor_usd', '') or '—'}  ",
                f"**Financing citation (`value_source_url`):** "
                f"{comp.get('value_source_url', '') or '— *(set after review)*'}  ",
                "",
            ]
        )
        if links:
            md_lines.append("**Primary-source links:**")
            for label, url in links:
                md_lines.append(f"- [{label}]({url})")
        else:
            md_lines.append(
                "_No links yet — run `npm run tier:a:comps:queue -- --fetch` for this workbook._"
            )
        md_lines.extend(["", "---", ""])

    if fetch:
        write_link_cache(cache, merge=True)
    with QUEUE_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=QUEUE_FIELDS)
        writer.writeheader()
        writer.writerows(csv_rows)
    QUEUE_MD.write_text("\n".join(md_lines), encoding="utf-8")


def cmd_queue(args: argparse.Namespace) -> int:
    rows = build_queue(case_id=args.case_id, include_verified=args.include_verified)
    write_queue_files(rows, fetch=args.fetch)
    pending = sum(1 for r in rows if r.reason != "already_verified")
    print(f"Wrote {len(rows)} rows -> {QUEUE_CSV}")
    print(f"Wrote markdown workbook -> {QUEUE_MD}")
    print(f"Need web review: {pending}")
    if rows:
        first = rows[0]
        print(f"\nStart: python -m pipeline.tier_a.comp_web_review step --index {first.index}")
    return 0


def cmd_searches(args: argparse.Namespace) -> int:
    rows = build_queue(case_id=args.case_id, include_verified=True)
    if args.index:
        rows = [r for r in rows if r.index == args.index]
    if not rows:
        print("No rows matched.")
        return 1
    for item in rows:
        comp = item.comparable
        name = comp.get("precedent_name", "")
        print(f"\n[{item.index}] {item.case_id} / {name}")
        for label, url in _search_queries(item.title_clean, name).items():
            print(f"  {label}: {url}")
    return 0


def _prompt(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{label}{suffix}: ").strip()
    return value or default


def cmd_step(args: argparse.Namespace) -> int:
    rows = build_queue(case_id=args.case_id)
    if not rows:
        print("Queue empty — nothing needs review.")
        return 0
    if args.index:
        selected = [r for r in rows if r.index == args.index]
    else:
        # Resume from first un-reviewed in findings
        findings_path = FINDINGS_CSV
        done: set[tuple[str, str]] = set()
        if findings_path.exists():
            for row in csv.DictReader(findings_path.open(encoding="utf-8")):
                if (row.get("action") or "").lower() in {"verify", "skip"}:
                    done.add((row["case_id"], row["precedent_rank"]))
        selected = [
            r
            for r in rows
            if (r.case_id, r.comparable.get("precedent_rank", "")) not in done
        ]
    if not selected:
        print("All queued rows have verify/skip in findings file.")
        return 0
    item = selected[0]
    comp = item.comparable
    name = comp.get("precedent_name", "")
    print(f"\n=== [{item.index}/{len(rows)}] {item.case_id} ===")
    print(f"Program: {item.title_clean}")
    print(f"Comparable #{comp.get('precedent_rank')}: {name}")
    print(f"Reason: {item.reason}\n")
    cache = load_link_cache()
    links = links_for_queue_row(comp, case_id=item.case_id, cache=cache, fetch=False)
    if links:
        print("Primary-source links:")
        for label, url in links:
            print(f"  {label}: {url}")
        print()
    print(
        f"{value_source_prompt()}\n"
        f"{inferred_financing_prompt(comp)}\n"
        "Do not paste google.com/search links.\n"
    )
    action = _prompt("action (verify/skip/note)", "verify").lower()
    if action == "skip":
        _append_finding(
            {
                "case_id": item.case_id,
                "precedent_rank": comp.get("precedent_rank", ""),
                "precedent_name": name,
                "action": "skip",
                "validation_status": comp.get("validation_status", "suggested"),
                "search_notes": _prompt("skip reason"),
            }
        )
        print("Recorded skip.")
        return 0
    vstatus = _prompt("validation_status", "verified" if action == "verify" else "estimated")
    anchor = _prompt("value_anchor_usd", comp.get("value_anchor_usd", ""))
    atype = _prompt(
        "value_anchor_type (total_raised|last_round|series_a|series_b|series_c|seed_round|grant|acquisition|market_cap)",
        default_anchor_type(comp),
    )
    source = _prompt("value_source_url", comp.get("value_source_url", ""))
    while source and _is_discovery_url(source):
        print("  That looks like a search-results URL. Paste the article/PR/SEC page instead.")
        source = _prompt_required("value_source_url")
    if vstatus == "verified" and not source:
        print("WARNING: verified requires value_source_url")
        source = _prompt_required("value_source_url")
        while _is_discovery_url(source):
            print("  That looks like a search-results URL. Paste the article/PR/SEC page instead.")
            source = _prompt_required("value_source_url")
    _append_finding(
        {
            "case_id": item.case_id,
            "precedent_rank": comp.get("precedent_rank", ""),
            "precedent_name": name,
            "action": action,
            "validation_status": vstatus,
            "value_anchor_usd": anchor,
            "value_anchor_type": atype,
            "value_source_url": source,
            "total_raised_usd_est": _prompt("total_raised_usd_est", comp.get("total_raised_usd_est", "")),
            "last_round_usd_est": _prompt("last_round_usd_est", comp.get("last_round_usd_est", "")),
            "inferred_financing": _prompt(
                inferred_financing_prompt(comp), comp.get("inferred_financing", "")
            ),
            "precedent_notes": _prompt("precedent_notes", comp.get("precedent_notes", "")),
            "search_notes": _prompt("search_notes (cite headline/source)"),
        }
    )
    print(f"\nSaved to {FINDINGS_CSV}")
    print(f"Next: python -m pipeline.tier_a.comp_web_review step --index {item.index + 1}")
    return 0


def _prompt_required(label: str) -> str:
    while True:
        value = input(f"{label}: ").strip()
        if value:
            return value
        print("  (required)")


def _append_finding(partial: dict[str, str]) -> None:
    TIER_A_ROOT.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []
    if FINDINGS_CSV.exists():
        rows = list(csv.DictReader(FINDINGS_CSV.open(encoding="utf-8")))
    key = (partial["case_id"], partial["precedent_rank"])
    rows = [r for r in rows if (r.get("case_id"), r.get("precedent_rank")) != key]
    row = {field: "" for field in FINDINGS_FIELDS}
    row.update(partial)
    row["reviewer"] = row.get("reviewer") or "interactive"
    row["reviewed_at"] = row.get("reviewed_at") or date.today().isoformat()
    rows.append(row)
    with FINDINGS_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FINDINGS_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _merge_precedent_notes(
    finding: dict[str, str],
    target: dict[str, str],
) -> None:
    """Apply curator notes; fold search_notes into precedent_notes when not duplicated."""
    notes = (finding.get("precedent_notes") or "").strip()
    search = (finding.get("search_notes") or "").strip()
    if notes:
        target["precedent_notes"] = notes
    if search:
        existing = (target.get("precedent_notes") or "").strip()
        if not existing:
            target["precedent_notes"] = search
        elif search not in existing:
            target["precedent_notes"] = f"{existing} — {search}"


def cmd_apply(args: argparse.Namespace) -> int:
    if not FINDINGS_CSV.exists():
        print(f"Missing {FINDINGS_CSV}; run step or edit findings CSV first.")
        return 1
    findings = list(csv.DictReader(FINDINGS_CSV.open(encoding="utf-8")))
    if not findings:
        print("Findings file is empty.")
        return 1
    comps = load_comparables()
    by_key = {(r["case_id"], r["precedent_rank"]): r for r in comps}
    applied = 0
    skipped = 0
    for finding in findings:
        action = (finding.get("action") or "").lower()
        key = (finding.get("case_id", ""), finding.get("precedent_rank", ""))
        if key not in by_key:
            print(f"WARN: no comparable for {key}")
            continue
        if action == "skip":
            skipped += 1
            continue
        if action not in {"verify", "note", "replace"}:
            continue
        target = by_key[key]
        for field in (
            "validation_status",
            "value_anchor_usd",
            "value_anchor_type",
            "value_source_url",
            "total_raised_usd_est",
            "last_round_usd_est",
            "inferred_financing",
        ):
            if (finding.get(field) or "").strip():
                target[field] = finding[field].strip()
        _merge_precedent_notes(finding, target)
        if action == "verify":
            target["validation_status"] = finding.get("validation_status") or "verified"
            target["confidence"] = "high"
            target["source"] = "tier_a_web_review"
        applied += 1
    write_comparables(list(by_key.values()))
    print(f"Applied {applied} comparable update(s), skipped {skipped}.")
    print("Run: npm run tier:a:build")
    return 0


def cmd_init_findings(args: argparse.Namespace) -> int:
    """Seed findings CSV from queue for spreadsheet editing."""
    rows = build_queue(case_id=args.case_id)
    TIER_A_ROOT.mkdir(parents=True, exist_ok=True)
    out: list[dict[str, str]] = []
    for item in rows:
        comp = item.comparable
        out.append(
            {
                "case_id": item.case_id,
                "precedent_rank": comp.get("precedent_rank", ""),
                "precedent_name": comp.get("precedent_name", ""),
                "action": "",
                "validation_status": "",
                "value_anchor_usd": "",
                "value_anchor_type": "",
                "value_source_url": "",
                "total_raised_usd_est": "",
                "last_round_usd_est": "",
                "inferred_financing": "",
                "precedent_notes": "",
                "reviewer": "",
                "reviewed_at": "",
                "search_notes": "",
            }
        )
    with FINDINGS_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FINDINGS_FIELDS)
        writer.writeheader()
        writer.writerows(out)
    print(f"Wrote {len(out)} blank findings rows -> {FINDINGS_CSV}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    q = sub.add_parser("queue", help="Export review queue CSV + markdown with primary-source links")
    q.add_argument("--case-id", help="Limit to one Tier A case")
    q.add_argument("--include-verified", action="store_true")
    q.add_argument(
        "--fetch",
        action="store_true",
        help="Web-resolve PR/SEC/market URLs (slow; updates comp_review_link_cache.csv)",
    )
    q.set_defaults(func=cmd_queue)

    s = sub.add_parser("searches", help="Print search URLs for queued rows")
    s.add_argument("--case-id")
    s.add_argument("--index", type=int)
    s.set_defaults(func=cmd_searches)

    st = sub.add_parser("step", help="Interactive review for next queued row")
    st.add_argument("--case-id")
    st.add_argument("--index", type=int, help="Queue index from comp_review_queue.csv")
    st.set_defaults(func=cmd_step)

    a = sub.add_parser("apply", help="Apply comp_review_findings.csv to comparables.csv")
    a.set_defaults(func=cmd_apply)

    init = sub.add_parser("init-findings", help="Blank findings spreadsheet from queue")
    init.add_argument("--case-id")
    init.set_defaults(func=cmd_init_findings)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
