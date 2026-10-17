#!/usr/bin/env python3
"""
Agent-overreach reports in public coding-agent issue trackers.

Pulls monthly denominators (all issues opened) and keyword-matched issues from
GitHub search, then builds a stratified random sample for hand-coding.

Requirements: Python 3.9+, the `gh` CLI logged in (`gh auth status`). No pip installs.

Steps (run from an empty folder):
  1. python pull_agent_issues.py collect               # ~25 min per repo; resumable (cache/)
  2. python pull_agent_issues.py summarise             # -> monthly.csv, phrase_counts.csv
  3. python pull_agent_issues.py sample --n 100        # -> coding_sample.csv

Design choices that matter for the analysis:
  - Searches title+body only (in:title,body). Default GitHub search also matches
    comments, and older issues have had longer to accumulate comments, which
    inflates early months.
  - Records labels, so duplicates can be excluded or kept. Duplicate labels are
    applied with a lag, so recent months are under-labelled; summarise reports both.
  - Records author type, so bot-filed issues can be checked.
  - Flags phrase-months where GitHub's 1,000-result cap truncates retrieval, and
    responses where GitHub reports incomplete_results.
"""

import argparse
import calendar
import csv
import hashlib
import json
import math
import os
import random
import subprocess
import sys
import time
from collections import defaultdict

DEFAULT_REPOS = ["anthropics/claude-code", "openai/codex", "google-gemini/gemini-cli"]

# Keyword families mirror the CLTR pilot's precursor behaviours (ignoring
# instructions, bypassing safeguards, deceiving users) plus destructive actions.
# Precision per family is unknown until hand-coded: treat these as a net, not a classifier.
FAMILIES = {
    "destructive": [
        "rm -rf",
        "deleted my",
        "deleted all",
        "deleted files",
        "wiped",
        "git reset --hard",
        "force push",
        "push --force",
        "drop table",
        "dropped the",
    ],
    "ignored_instruction": [
        "ignored my instructions",
        "ignores instructions",
        "ignoring instructions",
        "ignored the instruction",
        "despite being told",
        "explicitly told",
        "told it not to",
        "against my instructions",
    ],
    "safeguard_bypass": [
        "bypassed",
        "bypass the permission",
        "bypassing",
        "circumvent",
        "deny rule",
        "without permission",
        "without asking",
        "without approval",
    ],
    "misreport": [
        "lied",
        "lying",
        "pretended",
        "faked",
        "fabricated",
        "claimed it",
        "falsely claimed",
    ],
}

CACHE_DIR = "cache"
DENOM_FILE = "denominators.csv"
MATCH_FILE = "matches.jsonl"
_last_call = [0.0]


def months_between(start, end):
    y, m = map(int, start.split("-"))
    ey, em = map(int, end.split("-"))
    out = []
    while (y, m) <= (ey, em):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def month_range(month):
    y, m = map(int, month.split("-"))
    last = calendar.monthrange(y, m)[1]
    return f"{y:04d}-{m:02d}-01", f"{y:04d}-{m:02d}-{last:02d}"


def gh_search(q, page=1, per_page=100, min_interval=2.5):
    """GitHub issue search via `gh api`, cached on disk and rate-limited."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    key = hashlib.sha1(f"{q}|{page}|{per_page}".encode()).hexdigest()
    path = os.path.join(CACHE_DIR, key + ".json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    for attempt in range(6):
        wait = min_interval - (time.time() - _last_call[0])
        if wait > 0:
            time.sleep(wait)
        _last_call[0] = time.time()

        r = subprocess.run(
            [
                "gh",
                "api",
                "-X",
                "GET",
                "search/issues",
                "-f",
                f"q={q}",
                "-f",
                f"per_page={per_page}",
                "-f",
                f"page={page}",
            ],
            capture_output=True,
            text=True,
        )

        if r.returncode == 0:
            data = json.loads(r.stdout)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f)
            return data

        err = (r.stderr + r.stdout).lower()

        # 1. Catch transient network drops and TLS handshake timeouts FIRST
        is_network_error = any(
            s in err
            for s in (
                "connection reset",
                "tls handshake",
                "timeout",
                "dial tcp",
                "read tcp",
                "eof",
                "broken pipe",
                "temporary failure",
            )
        )
        if is_network_error:
            backoff = 5 * (attempt + 1)
            print(
                f"  network glitch (attempt {attempt + 1}): {r.stderr.strip()[:140]}; retrying in {backoff}s",
                file=sys.stderr,
            )
            time.sleep(backoff)
            continue

        # 2. Catch primary & secondary rate limits (including spam heuristics)
        if any(
            s in err
            for s in ("rate limit", "secondary", "403", "429", "abuse", "spammed")
        ):
            backoff = 60 * (attempt + 1)
            print(f"  rate-limited; sleeping {backoff}s", file=sys.stderr)
            time.sleep(backoff)
            continue

        # 3. Only raise invalid query if it is a genuine HTTP 422 and NOT a socket reset
        if ("422" in err or "validation failed" in err) and not is_network_error:
            # Let attempt retry once in case GitHub's search index is temporarily desynced
            if attempt < 2:
                time.sleep(5)
                continue
            raise RuntimeError(f"Invalid query: {q}\n{r.stderr}\n{r.stdout}")

        print(
            f"  gh error (attempt {attempt + 1}): {r.stderr.strip()[:200]}",
            file=sys.stderr,
        )
        time.sleep(5)

    raise RuntimeError(f"gh failed repeatedly for query: {q}")


def collect(args):
    months = months_between(args.start, args.end)
    denom_rows = []
    seen = set()
    if os.path.exists(MATCH_FILE):
        with open(MATCH_FILE, encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                seen.add((r["repo"], r["month"], r["phrase"], r["id"]))
    out = open(MATCH_FILE, "a", encoding="utf-8")
    for repo in args.repos:
        for month in months:
            a, b = month_range(month)
            base = f"repo:{repo} is:issue created:{a}..{b}"
            d = gh_search(base, per_page=1, min_interval=args.min_interval)
            denom_rows.append(
                {
                    "repo": repo,
                    "month": month,
                    "total_issues": d.get("total_count", 0),
                    "incomplete": d.get("incomplete_results", False),
                }
            )
            print(f"{repo} {month}: {d.get('total_count', 0)} issues", file=sys.stderr)
            if d.get("total_count", 0) == 0:
                continue
            for family, phrases in FAMILIES.items():
                for phrase in phrases:
                    q = f'{base} in:title,body "{phrase}"'
                    page, fetched = 1, 0
                    while True:
                        res = gh_search(q, page=page, min_interval=args.min_interval)
                        total = res.get("total_count", 0)
                        items = res.get("items", [])
                        for it in items:
                            k = (repo, month, phrase, it["id"])
                            if k in seen:
                                continue
                            seen.add(k)
                            out.write(
                                json.dumps(
                                    {
                                        "repo": repo,
                                        "month": month,
                                        "family": family,
                                        "phrase": phrase,
                                        "phrase_total": total,
                                        "truncated": total > 1000,
                                        "incomplete": res.get(
                                            "incomplete_results", False
                                        ),
                                        "id": it["id"],
                                        "number": it.get("number"),
                                        "url": it.get("html_url"),
                                        "title": it.get("title", ""),
                                        "created_at": it.get("created_at"),
                                        "state": it.get("state"),
                                        "state_reason": it.get("state_reason"),
                                        "labels": [
                                            l.get("name") for l in it.get("labels", [])
                                        ],
                                        "author": (it.get("user") or {}).get("login"),
                                        "author_type": (it.get("user") or {}).get(
                                            "type"
                                        ),
                                        "comments": it.get("comments"),
                                        "body_excerpt": (it.get("body") or "")[:800],
                                    }
                                )
                                + "\n"
                            )
                        fetched += len(items)
                        if not items or fetched >= min(total, 1000):
                            break
                        page += 1
            out.flush()
            # Flush denominators to disk immediately after each month
            write_csv(
                DENOM_FILE, denom_rows, ["repo", "month", "total_issues", "incomplete"]
            )
    out.close()
    write_csv(DENOM_FILE, denom_rows, ["repo", "month", "total_issues", "incomplete"])
    print(f"Wrote {DENOM_FILE} and {MATCH_FILE}", file=sys.stderr)


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def load_matches():
    rows = []
    with open(MATCH_FILE, encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line))
    return rows


def is_dup(r):
    return (
        any("duplicate" in (l or "").lower() for l in r["labels"])
        or r.get("state_reason") == "duplicate"
    )


def summarise(args):
    denoms = {}
    with open(DENOM_FILE, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            denoms[(r["repo"], r["month"])] = int(r["total_issues"])
    matches = load_matches()

    ids = defaultdict(set)  # (repo, month, family|ALL, variant) -> issue ids
    phrase_counts = defaultdict(int)
    bots = defaultdict(set)
    flags = defaultdict(set)
    for r in matches:
        key_rm = (r["repo"], r["month"])
        for fam in (r["family"], "ALL"):
            ids[key_rm + (fam, "all")].add(r["id"])
            if not is_dup(r):
                ids[key_rm + (fam, "excl_dup")].add(r["id"])
        if r.get("author_type") == "Bot":
            bots[key_rm].add(r["id"])
        if r.get("truncated"):
            flags[key_rm].add(f"truncated:{r['phrase']}")
        if r.get("incomplete"):
            flags[key_rm].add("incomplete_results")
        phrase_counts[
            (r["repo"], r["month"], r["family"], r["phrase"], r["phrase_total"])
        ] += 1

    fams = list(FAMILIES) + ["ALL"]
    out_rows = []
    for (repo, month), n in sorted(denoms.items()):
        row = {
            "repo": repo,
            "month": month,
            "total_issues": n,
            "bot_matches": len(bots[(repo, month)]),
            "flags": ";".join(sorted(flags[(repo, month)])),
        }
        for fam in fams:
            for variant in ("all", "excl_dup"):
                k = len(ids[(repo, month, fam, variant)])
                lo, hi = wilson(k, n)
                tag = f"{fam}_{variant}"
                row[f"{tag}_n"] = k
                row[f"{tag}_per1k"] = round(1000 * k / n, 2) if n else ""
                row[f"{tag}_per1k_lo"] = round(1000 * lo, 2) if n else ""
                row[f"{tag}_per1k_hi"] = round(1000 * hi, 2) if n else ""
        out_rows.append(row)
    fields = list(out_rows[0].keys()) if out_rows else ["repo", "month"]
    write_csv("monthly.csv", out_rows, fields)

    pc_rows = [
        {
            "repo": a,
            "month": b,
            "family": c,
            "phrase": d,
            "github_total": e,
            "retrieved": v,
        }
        for (a, b, c, d, e), v in sorted(phrase_counts.items())
    ]
    write_csv(
        "phrase_counts.csv",
        pc_rows,
        ["repo", "month", "family", "phrase", "github_total", "retrieved"],
    )
    print(
        "Wrote monthly.csv (rates per 1,000 issues, Wilson 95% CIs) and phrase_counts.csv",
        file=sys.stderr,
    )


def quarter(month):
    y, m = map(int, month.split("-"))
    return f"{y}Q{(m - 1) // 3 + 1}"


def sample(args):
    matches = load_matches()
    by_issue = {}
    for r in matches:
        if args.repo and r["repo"] != args.repo:
            continue
        k = (r["repo"], r["id"])
        if k not in by_issue:
            by_issue[k] = dict(r, families=set(), phrases=set())
        by_issue[k]["families"].add(r["family"])
        by_issue[k]["phrases"].add(r["phrase"])
    strata = defaultdict(list)
    for k, r in by_issue.items():
        strata[quarter(r["month"])].append(r)
    rng = random.Random(args.seed)
    qs = sorted(strata)
    per = max(
        1, args.n // max(1, len(qs))
    )  # equal allocation: lets you test whether precision drifts over time
    chosen = []
    for q in qs:
        pool = sorted(strata[q], key=lambda r: (r["repo"], r["id"]))
        chosen += rng.sample(pool, min(per, len(pool)))
    rows = []
    for r in chosen:
        rows.append(
            {
                "repo": r["repo"],
                "number": r["number"],
                "url": r["url"],
                "created_at": r["created_at"],
                "quarter": quarter(r["month"]),
                "stratum_size": len(strata[quarter(r["month"])]),
                "families_matched": "|".join(sorted(r["families"])),
                "phrases_matched": "|".join(sorted(r["phrases"])),
                "title": r["title"],
                "labels": "|".join(r["labels"]),
                "author_type": r["author_type"],
                "body_excerpt": r["body_excerpt"].replace("\r", " ").replace("\n", " "),
                "code_category": "",
                "safeguards_disabled_by_user": "",
                "irreversible": "",
                "evidence_quote": "",
                "notes": "",
            }
        )
    write_csv("coding_sample.csv", rows, list(rows[0].keys()) if rows else ["url"])
    print(
        f"Wrote coding_sample.csv: {len(rows)} issues, {per} per quarter, seed {args.seed}.",
        file=sys.stderr,
    )
    print("Weight by stratum_size when estimating overall precision.", file=sys.stderr)


def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("collect")
    c.add_argument("--repos", nargs="+", default=DEFAULT_REPOS)
    c.add_argument("--start", default="2025-03")
    c.add_argument("--end", default="2026-09", help="last complete month")
    c.add_argument(
        "--min-interval", type=float, default=2.1, help="seconds between API calls"
    )
    sub.add_parser("summarise")
    s = sub.add_parser("sample")
    s.add_argument("--n", type=int, default=100)
    s.add_argument("--seed", type=int, default=2026)
    s.add_argument("--repo", default=None, help="restrict to one repo")
    args = p.parse_args()
    {"collect": collect, "summarise": summarise, "sample": sample}[args.cmd](args)


if __name__ == "__main__":
    main()
