#!/usr/bin/env python3
"""System design practice runner.

Creates an attempt sheet for a case, prints the prompt, and runs a phase timer.
Standard library only. See README.md in this folder.

    python3 practice.py list
    python3 practice.py random [--family D]
    python3 practice.py start <case-id-prefix> [--minutes 45] [--no-timer]
    python3 practice.py timer [--family A] [--minutes 45]
    python3 practice.py phases
"""

import argparse
import datetime as dt
import random
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROMPTS = ROOT / "prompts"
ATTEMPTS = ROOT / "attempts"
TEMPLATE = ROOT / "templates" / "attempt.md"

FAMILY_NAMES = {
    "A": "Product design",
    "B": "Infrastructure / component design",
    "C": "Low-level / object-oriented design",
    "D": "Device / systems design",
    "E": "Design-then-code",
}

# Each phase: (name, minutes in a 45-minute session, what to produce).
SKELETON = [
    ("1. Requirements", 5, "Functional (2-4 core features) + non-functional WITH numbers + out of scope. Say them out loud."),
    ("2. Interface", 5, "API endpoints / function signatures / hardware-driver contract. One example call with its exact result."),
    ("3. State", 3, "Core entities. Where each piece of state lives, and who writes it."),
    ("4. Trace one flow", 5, "One request or event end to end, naming every component it passes through."),
    ("5. Components", 10, "The diagram that makes step 4 work. Simple first. Every box tied to a requirement."),
    ("6. Deep dive", 10, "The hardest constraint from step 1: at least two options, pick one, say why and what it costs."),
    ("7. Failures and trade-offs", 5, "What breaks, what the system does then, what changes at 10x."),
    ("Wrap-up", 2, "Summarize the design and its biggest trade-off in three sentences, out loud."),
]

LOW_LEVEL = [
    ("1. Requirements", 5, "What the system must do (use cases), what's out of scope, what must be easy to extend."),
    ("2. Entities and relationships", 5, "The nouns, who owns whom, one responsibility per class."),
    ("3. Class APIs", 8, "Public methods with inputs and outputs for the main classes."),
    ("4. State and transitions", 7, "The state each object holds and the transitions (draw the state machine)."),
    ("5. Walk one use case", 10, "Follow one use case through the classes, method call by method call."),
    ("6. Extensibility", 5, "Pick one new requirement. Show exactly what changes and what doesn't."),
    ("7. Edge cases and concurrency", 3, "Invalid inputs, full/empty, two actors at once."),
    ("Wrap-up", 2, "Summarize the design and its main extension point, out loud."),
]

CODING = [
    ("1. Clarify and interface", 5, "Exact signature. What each input stands for, and its valid range."),
    ("2. Examples", 5, "One example call with its EXACT output, then 2-3 edge examples."),
    ("3. Approach and invariant", 5, "Data structure; what each field stands for; the invariant that holds after every call."),
    ("4. Code", 18, "Write it. Name every intermediate quantity."),
    ("5. Trace and test", 7, "Run your examples by hand through the code (state table). Then one edge case."),
    ("6. Complexity and follow-ups", 3, "Time and space. Thread safety? Memory growth? Clock issues?"),
    ("Wrap-up", 2, "Explain the design in three sentences, out loud."),
]

PHASES = {"A": SKELETON, "B": SKELETON, "D": SKELETON, "C": LOW_LEVEL, "E": CODING}

CROSS_CUTTING = [
    "X1. Drove and talked aloud",
    "X2. Trade-offs said aloud",
    "X3. Time (reached the last step)",
]

META_RE = re.compile(r"<!--\s*(.*?)\s*-->", re.S)


# ---------------------------------------------------------------- cases

def parse_case(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    meta = {"id": path.stem, "family": "?", "level": "", "minutes": "45", "bridge": ""}
    m = META_RE.search(text)
    if m:
        for part in m.group(1).split("|"):
            if ":" in part:
                k, v = part.split(":", 1)
                meta[k.strip()] = v.strip()
    title = next((ln[2:].strip() for ln in text.splitlines() if ln.startswith("# ")), path.stem)
    meta["title"] = title
    meta["path"] = path
    meta["prompt"] = extract_section(text, "## The prompt")
    return meta


def extract_section(text: str, heading: str) -> str:
    lines = text.splitlines()
    out, inside = [], False
    for ln in lines:
        if ln.strip() == heading:
            inside = True
            continue
        if inside and ln.startswith("## "):
            break
        if inside:
            out.append(ln)
    return "\n".join(out).strip()


def all_cases() -> list:
    return [parse_case(p) for p in sorted(PROMPTS.glob("*.md")) if p.name != "README.md"]


def find_case(prefix: str) -> dict:
    prefix = prefix.lower()
    matches = [c for c in all_cases() if c["id"].lower().startswith(prefix)]
    if not matches:
        sys.exit(f"No case starts with '{prefix}'. Run: python3 practice.py list")
    if len(matches) > 1:
        names = ", ".join(c["id"] for c in matches)
        sys.exit(f"'{prefix}' matches several cases: {names}. Use a longer prefix.")
    return matches[0]


def attempt_count(case_id: str) -> int:
    if not ATTEMPTS.exists():
        return 0
    n = 0
    for d in ATTEMPTS.iterdir():
        # folder names look like 2026-11-07_a01_url_shortener (optionally _2, _3 …)
        if d.is_dir() and len(d.name) > 11 and d.name[11:].startswith(case_id):
            n += 1
    return n


# ---------------------------------------------------------------- commands

def cmd_list(_args):
    cases = all_cases()
    print(f"{'id':<32} {'fam':<4} {'level':<12} {'tries':<6} title")
    print("-" * 90)
    for c in cases:
        print(f"{c['id']:<32} {c['family']:<4} {c['level']:<12} {attempt_count(c['id']):<6} {c['title']}")


def cmd_random(args):
    cases = all_cases()
    if args.family:
        cases = [c for c in cases if c["family"].upper() == args.family.upper()]
    if not cases:
        sys.exit("No cases for that family.")
    fewest = min(attempt_count(c["id"]) for c in cases)
    pool = [c for c in cases if attempt_count(c["id"]) == fewest]
    c = random.choice(pool)
    print(f"Suggested: {c['id']}  ({c['title']}, family {c['family']}, attempted {fewest}x)")
    print(f"Start it:  python3 practice.py start {c['id'].split('_')[0]}")


def cmd_phases(_args):
    for fam in "ABCDE":
        print(f"\nFamily {fam}: {FAMILY_NAMES[fam]}")
        for name, mins, what in PHASES[fam]:
            print(f"  {mins:>2} min  {name:<32} {what}")


def build_sheet(case: dict, minutes: float) -> str:
    phases = PHASES.get(case["family"].upper(), SKELETON)
    steps = []
    for name, mins, what in phases:
        if name == "Wrap-up":
            continue
        steps.append(f"## {name} (~{scaled(mins, minutes):.0f} min)\n\n> {what}\n\n\n")
    rows = [f"| {name} | | |" for name, _, _ in phases if name != "Wrap-up"]
    rows += [f"| {x} | | |" for x in CROSS_CUTTING]
    template = TEMPLATE.read_text(encoding="utf-8")
    return template.format(
        title=case["title"],
        case_id=case["id"],
        family=case["family"],
        date=dt.date.today().isoformat(),
        minutes=f"{minutes:g}",
        prompt=case["prompt"] or "(see the case file)",
        steps="\n".join(steps).rstrip() + "\n",
        score_rows="\n".join(rows),
    )


def new_attempt_dir(case_id: str) -> Path:
    ATTEMPTS.mkdir(exist_ok=True)
    base = f"{dt.date.today().isoformat()}_{case_id}"
    d, n = ATTEMPTS / base, 2
    while d.exists():
        d = ATTEMPTS / f"{base}_{n}"
        n += 1
    d.mkdir()
    return d


def cmd_start(args):
    case = find_case(args.case)
    d = new_attempt_dir(case["id"])
    sheet = d / "attempt.md"
    sheet.write_text(build_sheet(case, args.minutes), encoding="utf-8")
    rel = sheet.relative_to(ROOT)
    print("=" * 78)
    print(f"{case['title']}   (family {case['family']}: {FAMILY_NAMES.get(case['family'].upper(), '?')})")
    print("=" * 78)
    print(case["prompt"])
    print("=" * 78)
    print(f"Attempt sheet: {rel}")
    print("Don't open the case file's hidden notes until you've finished the self-review.")
    if args.no_timer:
        return
    input("\nPress Enter to start the clock (Ctrl-C at any time to stop)... ")
    run_timer(PHASES.get(case["family"].upper(), SKELETON), args.minutes, d / "timer_log.txt")


def cmd_timer(args):
    fam = (args.family or "A").upper()
    input(f"Family {fam} timer, {args.minutes:g} min. Press Enter to start... ")
    run_timer(PHASES.get(fam, SKELETON), args.minutes, None)


# ---------------------------------------------------------------- timer

def scaled(phase_minutes: float, total_minutes: float) -> float:
    return phase_minutes * total_minutes / 45.0


def fmt(seconds: float) -> str:
    seconds = max(0, int(round(seconds)))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def run_timer(phases, total_minutes: float, log_path):
    log = []
    start = time.monotonic()
    wall_start = dt.datetime.now()
    log.append(f"start {wall_start:%Y-%m-%d %H:%M:%S}, planned {total_minutes:g} min")
    reached = None
    try:
        for name, mins, what in phases:
            reached = name
            secs = scaled(mins, total_minutes) * 60
            elapsed_total = time.monotonic() - start
            log.append(f"{fmt(elapsed_total)}  entered {name}")
            print("\a")  # terminal bell
            print(f"\n>>> {name}  ({fmt(secs)})")
            print(f"    {what}")
            phase_end = time.monotonic() + secs
            while True:
                left = phase_end - time.monotonic()
                if left <= 0:
                    break
                total = time.monotonic() - start
                sys.stdout.write(f"\r    left in phase {fmt(left)}   |   elapsed {fmt(total)}   ")
                sys.stdout.flush()
                time.sleep(min(1.0, left))
            sys.stdout.write("\r" + " " * 60 + "\r")
        print("\a\nTime. Stop, then do the self-review in attempt.md before opening anything.")
        log.append(f"{fmt(time.monotonic() - start)}  finished all phases")
    except KeyboardInterrupt:
        total = time.monotonic() - start
        print(f"\n\nStopped at {fmt(total)} during '{reached}'.")
        log.append(f"{fmt(total)}  stopped early during {reached}")
    if log_path is not None:
        log_path.write_text("\n".join(log) + "\n", encoding="utf-8")
        print(f"Timer log: {log_path.relative_to(ROOT)}")


# ---------------------------------------------------------------- main

def main():
    p = argparse.ArgumentParser(description="System design practice runner")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="list all cases").set_defaults(fn=cmd_list)

    r = sub.add_parser("random", help="suggest a least-attempted case")
    r.add_argument("--family", help="A, B, C, D or E")
    r.set_defaults(fn=cmd_random)

    s = sub.add_parser("start", help="start an attempt")
    s.add_argument("case", help="case id or prefix, e.g. a01")
    s.add_argument("--minutes", type=float, default=45)
    s.add_argument("--no-timer", action="store_true")
    s.set_defaults(fn=cmd_start)

    t = sub.add_parser("timer", help="just the phase timer")
    t.add_argument("--family", help="A, B, C, D or E (default A)")
    t.add_argument("--minutes", type=float, default=45)
    t.set_defaults(fn=cmd_timer)

    sub.add_parser("phases", help="show the phase plan per family").set_defaults(fn=cmd_phases)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
