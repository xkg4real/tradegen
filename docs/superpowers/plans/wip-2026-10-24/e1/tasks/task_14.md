### Task 14: Owner-gated final steps (the daily-task prompt, the owner acts, the first live poll, the notes)

**Files:**
- Repo: none. This task changes no repo file, with one exception: when Step 5 or Step 6 stops on a finding (E1R2-5,
  E1R2-6, E1R2-7, a refusal of E1's own request or a crash), Step 7 adds one line per finding to
  `docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md` (anchor: Task 13's
  `## Round-2 rulings as applied` heading, so the lines end the "Deferred minors" section; LF) and commits that file
  alone, never on `main` (once E1 is merged, on a new branch `e1-live-findings`).
- Outside the repo, through the scheduled-tasks tool only (never by editing its files): the prompt of the scheduled
  task `tradegen-compliance-daily` (Step 4, only after the owner's explicit yes).
- Outside the repo, with the Edit tool (all three are LF on 2026-10-28; the Edit tool keeps each file's endings;
  never `sed -i`, never a heredoc append):
  - `C:/Users/whydi/.claude/projects/C--Users-whydi-OneDrive-Desktop-TRADEGEN/memory/plans-2026-10-24-decisions.md`
    (anchor: its last line);
  - `C:/Users/whydi/.claude/projects/C--Users-whydi-OneDrive-Desktop-TRADEGEN/memory/MEMORY.md` (anchor: the
    `[2026-10-24 plan decisions]` line);
  - `C:/Users/whydi/AppData/Roaming/Claude/side-session-notes/local_bff3b8df-9985-4987-9c98-f6c7486d410f/tradegen-phase-a.md`
    (anchor: its last line).
- Scratch, outside the repo (LF, created with the Write tool): `<S>/e1_daily_prompt.py` and
  `<S>/e1_daily_prompt.txt`, where `<S>` is a new folder `e1_task14` in this session's scratchpad directory (the
  system prompt names it). Shell variables do not persist between Bash calls, so write `<S>` out in full, with
  forward slashes, in every command.
- Test: none. This task adds no repo code and no test, so the usual failing-test cycle does not apply; its steps are
  owner gates. Its one piece of Python, the Step 2 helper, lives in the scratch folder, reads two files, writes
  nothing and checks its own input against a pinned hash.

**Interfaces:**
- Consumes:
  - Task 12: `python -m execution.poll --once`, which prints one line (or two `{"crash": ...}` lines when the crash
    path itself failed, E40): either the summary of contract 16.3,
    `{"utc": "<YYYY-MM-DDTHH:MM:SSZ>", "venues": {"kis": "ok" | "error", "upbit": "ok" | "error", "okx": "ok" |
    "error"}, "errors": {"<venue>": "<error text>"}, "counts": {"<venue>": {"holdings": n, "open_orders": n,
    "fills": n, "deposits": n, "withdrawals": n, "addresses": n}}, "evidence": n | "broken", "alerts": n,
    "not_set": [<items>]}` (exit 0); or
    `another E1 poller holds poll.lock; exiting` (exit 0, nothing polled; E1R2-1); or
    `{"crash": "<TypeName>", "at": "<file>:<line>"}` (exit 4). Also `--pending` and `--mark-sent <utc>`, which only
    the daily prompt runs (contract 16.4, E23).
  - The error texts a summary can carry (E37: names, paths, HTTP statuses and venue codes only, never a value):
    `keys missing: <NAME>` (Tasks 5 to 7, E31); `code not signed` (Task 5, E42);
    `okx self-check failed: <names>` with `<names>` taken from `perm`, `acctLv`, `enableSpotBorrow`, `autoLoan`,
    `ip`, in that order, joined by `, ` (Task 7); `<venue>: <path>: field <name>` and
    `<venue>: <path>: <TypeName>` (the parsers, E37); `kis: KIS account number is not 8 + 2 digits` (Task 5);
    `<venue> <path>: HTTP <status>` with an optional ` <code>` after it, plus `: not JSON` when the body was not
    JSON (transport, Task 3, E15); `<venue> <path>: <TypeName>` (a send that failed, Task 3); and the rest of
    transport's `InquiryRefused` and `InquiryError` texts (Tasks 2 and 3).
  - `transport.AUTH_CODES` (Task 2, `execution/transport.py`): read it from the source when an error carries a
    venue code; never import `execution.keys`.
  - The `not_set` items (Task 11, `checks.NOT_SET_ITEMS`): `"<Venue>: keys not in .env"`, `"KIS: code not signed"`,
    `"FLOOR: not set"`, `"DAILY_LOSS: not set"`, `"OKX_CAP: not set"`, the same three with `no live positions`,
    and `"ADDRESS_LIST: owner log not OK"`.
  - Task 1: the ledger. Task 13: its commit `test: E1 full run, README rows and the execution ledger` (the full
    run, the README and `qa/acceptance_results.json`), the ledger's four sections in order (`## Drift rulings`,
    `## Deferred minors`, `## Round-2 rulings as applied`, `## Runs`) and its totals line under `## Runs`, which
    holds `execution <n> PASS`.
  - The scheduled-tasks tools `list_scheduled_tasks` (each task's `taskId`, `enabled`, `path` to its SKILL.md and,
    when that file could not be read, `notRead`), `update_scheduled_task(taskId, prompt)` and
    `run_scheduled_task(taskId)`; load them with ToolSearch when they are deferred.
- Produces: no repo name. Outside the repo: the approved prompt of `tradegen-compliance-daily` (on a yes), and the
  memory and hand-over notes that the next session reads. In the ledger, only on a finding: one line per finding.

**Plan decisions used:** E7 (X7: the daily-prompt change is the last task's owner gate), E9 (X9: the owner acts
verbatim; the first live `--once` only after the owner's word; a redacted summary), E23 (`--pending` and
`--mark-sent` in the prompt), E31 and E1R2-8 (`keys missing`, one amber KEY_MISSING a day), E35 (the ledger), E37
(error texts carry no value), E42 and E1R2-9 (KIS sends nothing until the code is signed), E1R2-1 (a held lock exits
0), E1R2-5 (a live field mismatch fails the venue closed and goes to a follow-up task), E1R2-6 (OKX `autoLoan` on a
spot-mode key: stop and ask), E1R2-7 (KIS overseas service not enabled: stop and ask), E40 (a crash whose rows cannot
be written still shows). Round-3 rulings G3-1 (counts) and G3-3 (the public repo; the controller pushes). Contract
sections 0.1, 0.2, 16.3, 18 and 19.

Notes for the implementer (read before starting):
- Step 3 is the question that opens the gates; Steps 4 to 7 wait on the owner. Each of them starts only on the
  owner's own words in chat, and they may come in any order and in a later session, so Steps 5 and 6 run Step 5's
  checkout check before their poll and Step 7 before its Edit. Step 8 runs before this session ends, whatever is
  still open, and runs again whenever a later step happens in a later session (editing its own block in place).
- Claude performs none of the six owner acts. It never opens, reads, greps or prints `.env`, never asks for a key,
  never runs `tools/signer/sign.py`, never creates the Windows Task Scheduler task, never starts the long-running
  poller (`python -m execution.poll` without `--once`) and never stops one that the owner started (contract 0.1).
- The only network calls this plan ever makes are the `--once` runs of Steps 5 and 6 (contract 0.2). They run
  without the KEYLESS prefix, behind the QUANTGEN overlap check of contract 0.3, with the Bash tool's
  `run_in_background: true`, then wait for the exit notification (never poll the output file). One `--once` makes
  at most 37 GET calls (KIS 9, Upbit 8, OKX 20) and the KIS token POST, paced at 5 a second, each attempt with a
  10 s timeout and a GET retried at most once after 2 s; each venue stops at its first failed call. With every
  first attempt timing out and every retry answering just in time, that is about 37 x 22.4 s + 10.2 s, about 14
  minutes, over the 10-minute foreground limit (and `requests`' timeout bounds each socket read, not a whole
  request); a killed run would lose the report of the one approved live call.
- Report only what the summary line holds: venues, ok or error, the error texts, the counts, the evidence count,
  the fresh-alert count and `not_set`. Never open, `cat`, `grep` or quote `~/.tradegen/execution/inquiry-*.jsonl`,
  `evidence.jsonl` or `alerts.jsonl`, or `~/.tradegen/kis_token.json`: they hold balances, addresses or the token.
  `ls` (names only) is enough.
- Every message this task sends the owner, a stop or a "tell the owner" included, ends with the two closing
  sentences of Step 3 (the real odds, then "This is not legal or investment advice; I am not a licensed advisor.").
- Never loosen a check, a guard or an allowlist to make a live venue pass. A code change found here is a new
  follow-up task under this plan's rules: a failing test first, the DRIFT RULE, and a new signature by the owner,
  because `execution/*.py` is in the D14 code hash (Task 9).

- [ ] **Step 1: Pre-flight (read only)**

  From the repo root `C:/Users/whydi/OneDrive/Desktop/TRADEGEN` in Git Bash:

```bash
git status --short
git branch --show-current
git log -1 --format='%h %s'
grep -c '^## ' docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md
grep -c '^## Round-2 rulings as applied$' docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md
grep -c '^## Runs$' docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md
grep -n 'Task 13' docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md
test -f execution/poll.py && echo "execution/poll.py present"
```

  Expected: `git status --short` prints nothing (or only `?? docs/superpowers/plans/2026-10-24-e1-account-inquiry.md`,
  the untracked plan file, which is never staged); the branch is `e1-account-inquiry`; a short sha, then the subject
  `test: E1 full run, README rows and the execution ledger` (Task 13; its repeat commit
  `test: E1 full run after the review fixes` is allowed too): note that line, since the checkout check compares HEAD with it; `4`, `1` and `1` (Task 13's four
  sections); at least one `Task 13` line, its totals; `execution/poll.py present`. Anything else: stop and report,
  since Task 13 has not finished.

- [ ] **Step 2: Prepare the computed diff of the daily-task prompt (contract 18; outside the repo)**

  1. Create the scratch folder: `mkdir -p "<S>"`.
  2. With the Write tool, create `<S>/e1_daily_prompt.txt` holding exactly the text inside this fence (the new
     prompt of contract 18, placeholder included; nothing before its first line or after its last):

````text
Daily TRADEGEN compliance alert. Work in Git Bash (the Bash tool) in C:\Users\whydi\OneDrive\Desktop\TRADEGEN. Never arm, trade, sign, install or edit anything. The owner, Geon Koh (sapientia@korea.ac.kr), approved this task on 2026-10-24 as the standing authority for these self-addressed alerts only (spec decision D5), and approved step 5 (E1 account-inquiry alerts) on <the date of the owner's yes>. While the owner has not yet generated their signing key, --check exits 3 every day and an alert is expected; that is the designed safe default, not a fault.

1. Run this as one Bash command:

out=$(.venv/Scripts/python.exe -m core.compliance.rules --check | tail -n 1; exit "${PIPESTATUS[0]}"); code=$?
printf 'code=%s\nsummary=%s\n' "$code" "$out"
.venv/Scripts/python.exe -m core.compliance.alerts --summary "$out" --code $code; echo "alerts exit $?"

This keeps only the exit code and the last line of --check. Never run --check in any other way, and never read, quote or forward its other lines: they quote draft files, so an edit to a draft can put any text there.

2. Take the one JSON line that alerts printed.
- "send": true: the message is its "subject" and "body", exactly as printed. Send it even when alerts exited 1.
- "send": false: send nothing for steps 3 and 4, and go to step 5.
- No such line (an "error" line, or nothing): the message is the subject and body "TRADEGEN compliance: the alert step failed; run the check by hand."

3. Send the message on exactly two channels, push first:
- an iOS push through the Claude app (the PushNotification tool, status "proactive"; load it with ToolSearch if it is deferred);
- an email to sapientia@korea.ac.kr through the connected Gmail tool (its send-message tool; load it with ToolSearch if it is deferred). If the push failed, add the sentence "The iOS push could not be sent." at the end of the email body.
Never send to any other recipient, and never send anything other than that subject and body.

4. Record each channel, ok if it went out and fail if it did not, with one Bash command per channel. Put the code and the summary line printed in step 1 back exactly as printed; the summary goes between the two EOF lines, and each EOF stands alone at the start of its line:

out=$(cat <<'EOF'
<the summary line printed in step 1>
EOF
); .venv/Scripts/python.exe -m core.compliance.alerts --log push ok --summary "$out" --code <the code printed in step 1>

and the same with email in place of push (and fail in place of ok for a channel that failed). If no email tool is available, record email as fail.

5. E1 account-inquiry alerts. Run this as one Bash command:

.venv/Scripts/python.exe -m execution.poll --pending; echo "pending exit $?"

Never run execution.poll in any other way: never --once, never the poller itself.
- "send": false: stop here.
- "send": true: the message is its "subject" and "body", exactly as printed. Send it on the same two channels as step 3, push first, to the same single recipient, with the same rule for a failed push.
- No such line (an "error" line, or nothing): the message is the subject and body "TRADEGEN E1: the pending-alert step failed; run python -m execution.poll --pending by hand." Send it as in step 3 and mark nothing.
- If at least one of the two channels went out, run one Bash command for each value in the printed "utcs" list:

.venv/Scripts/python.exe -m execution.poll --mark-sent <the utc value>

If both channels failed, mark nothing: the same rows are sent again tomorrow.

Files you may change: only ~/.tradegen/compliance/alerts.jsonl (rows that alerts appends), ~/.tradegen/compliance/owner.jsonl.lock (the empty lock file the first logged alert creates), ~/.tradegen/compliance/snapshots (written by --check when the state is valid), ~/.tradegen/execution/alerts.jsonl (rows that --mark-sent marks sent), ~/.tradegen/execution/alerts.jsonl.lock and the temporary ~/.tradegen/execution/.alerts.jsonl.*.tmp file --mark-sent writes and renames. Nothing else.
````

  3. With the Write tool, create `<S>/e1_daily_prompt.py`. Its `NEW_SHA256` pins the text above, so a copying slip
     in step 2 is caught; the three `CHANGES` and `STEP5` (E1's four changes) take E1's changes back out, so a live
     prompt that changed anywhere else since 2026-10-24 is caught as well:

```python
"""E1 Task 14: the computed diff of the live tradegen-compliance-daily prompt against CONTRACT 18's new prompt.

python e1_daily_prompt.py diff LIVE NEW          exit 0: NEW is the pinned text and LIVE is the 2026-10-24 prompt;
                                                 prints the unified diff (live -> new). Exit 0 with one line when
                                                 LIVE is already NEW with a date filled in. Exit 1 otherwise.
python e1_daily_prompt.py verify LIVE NEW DATE   exit 0: LIVE is NEW with DATE (YYYY-MM-DD) in place of the
                                                 placeholder. Exit 1 otherwise, with the diff.
LIVE is the task's SKILL.md (front matter and CRLF allowed); NEW is the prompt text alone. Reads two files, writes
nothing, makes no network call.
"""
from __future__ import annotations

import difflib
import hashlib
import re
import sys
from pathlib import Path

PLACEHOLDER = "<the date of the owner's yes>"
NEW_SHA256 = "be50e3ec73439f788395335dcb8a9fde80431cfbbbb8461c3fda5eeea688dbe7"
# E1's changes to the 2026-10-24 prompt (CONTRACT 18), each as (2026-10-24 text, new text); step 5 is the fourth.
CHANGES = (
    (" (spec decision D5). While",
     f" (spec decision D5), and approved step 5 (E1 account-inquiry alerts) on {PLACEHOLDER}. While"),
    ('- "send": false: send nothing and stop here.',
     '- "send": false: send nothing for steps 3 and 4, and go to step 5.'),
    (" (the empty lock file the first logged alert creates) and ~/.tradegen/compliance/snapshots (written by"
     " --check when the state is valid). Nothing else.",
     " (the empty lock file the first logged alert creates), ~/.tradegen/compliance/snapshots (written by"
     " --check when the state is valid), ~/.tradegen/execution/alerts.jsonl (rows that --mark-sent marks sent),"
     " ~/.tradegen/execution/alerts.jsonl.lock and the temporary ~/.tradegen/execution/.alerts.jsonl.*.tmp file"
     " --mark-sent writes and renames. Nothing else."),
)
STEP5 = re.compile(r"\n\n5\. E1 account-inquiry alerts\..*?(?=\n\nFiles you may change:)", re.S)
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def body(text: str) -> str:
    """The prompt without SKILL.md front matter, with LF endings and no leading or trailing blank lines."""
    text = text.replace("\r\n", "\n")
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end < 0:
            raise ValueError("the front matter is not closed")
        text = text[end + 5:]
    return text.strip("\n")


def base_of(new: str) -> str:
    """The 2026-10-24 prompt: NEW with E1's four changes taken out."""
    old = new
    for before, after in CHANGES:
        if old.count(after) != 1:
            raise ValueError(f"the new prompt does not hold exactly one {after[:50]!r}")
        old = old.replace(after, before)
    old, n = STEP5.subn("", old)
    if n != 1:
        raise ValueError("the new prompt does not hold exactly one step 5")
    return old


def diff(a: str, b: str, a_name: str, b_name: str) -> str:
    """A unified diff of two prompts, line by line."""
    return "\n".join(difflib.unified_diff(a.split("\n"), b.split("\n"), a_name, b_name, lineterm=""))


def main(argv: list[str]) -> int:
    if len(argv) not in (3, 4) or argv[0] not in ("diff", "verify") or (argv[0] == "verify") != (len(argv) == 4):
        print("usage: diff LIVE NEW | verify LIVE NEW DATE")
        return 1
    live = body(Path(argv[1]).read_text(encoding="utf-8"))
    new = body(Path(argv[2]).read_text(encoding="utf-8"))
    if hashlib.sha256(new.encode("utf-8")).hexdigest() != NEW_SHA256:
        print("NEW is not the plan's prompt text: copy it again, exactly")
        return 1
    if argv[0] == "diff":
        done = re.fullmatch(re.escape(new).replace(re.escape(PLACEHOLDER), r"(\d{4}-\d{2}-\d{2})"), live)
        if done:
            print(f"the live prompt is already the approved prompt, dated {done.group(1)}: nothing to change")
            return 0
        if live != base_of(new):
            print("the live prompt changed outside E1's four changes since 2026-10-24: stop and rule")
            print(diff(base_of(new), live, "2026-10-24 prompt", "live prompt"))
            return 1
        print(diff(live, new, "live prompt", "new prompt"))
        return 0
    if not DATE.fullmatch(argv[3]):
        print("DATE must be YYYY-MM-DD")
        return 1
    approved = new.replace(PLACEHOLDER, argv[3])
    if live != approved:
        print(diff(approved, live, "approved prompt", "live prompt"))
        return 1
    print(f"the live prompt is the approved prompt, dated {argv[3]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

  4. Load the scheduled-tasks tools with ToolSearch
     (`select:mcp__scheduled-tasks__list_scheduled_tasks,mcp__scheduled-tasks__update_scheduled_task,mcp__scheduled-tasks__run_scheduled_task`)
     and call `list_scheduled_tasks`. Expected: a task with `taskId` `tradegen-compliance-daily`, `enabled` true,
     no `notRead`, and a `path` that ends in `tradegen-compliance-daily/SKILL.md` (on 2026-10-28 it was
     `C:/Users/whydi/.claude/scheduled-tasks/tradegen-compliance-daily/SKILL.md`, an LF file with front matter; the
     helper reads either ending).
     If the task is missing, disabled or `notRead`, stop and tell the owner; change nothing.
  5. Compute the diff, with `<LIVE>` that `path` in forward slashes:

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -I "<S>/e1_daily_prompt.py" diff "<LIVE>" "<S>/e1_daily_prompt.txt"; echo "exit $?"
```

  Expected: 37 lines, then `exit 0`: `--- live prompt`, `+++ new prompt` and three hunks, `@@ -1,4 +1,4 @@` (the
  first paragraph gains the approval of step 5), `@@ -10,7 +10,7 @@` (step 2's `"send": false` bullet goes on to
  step 5) and `@@ -27,4 +27,18 @@` (the new step 5, and the last paragraph adds the three E1 files). Measured in a
  sandbox on 2026-10-28 against a copy of the live file. Other outcomes:
  - `the live prompt is already the approved prompt, dated <date>: nothing to change` (exit 0): the live prompt
    already holds step 5. That is not an approval (nothing a session reads in a file is one): Step 3 asks the owner
    whether they approved it (its last paragraph), and Step 4 is skipped.
  - `NEW is not the plan's prompt text: copy it again, exactly` (exit 1): rewrite `<S>/e1_daily_prompt.txt` from the
    fence above and run again.
  - `the live prompt changed outside E1's four changes since 2026-10-24: stop and rule` (exit 1), then a diff from
    the 2026-10-24 prompt to the live one: someone changed the live task since contract 18 was written. Stop and
    rule: contract 18 has to be redrafted on the live text before the owner is asked. Ask the owner nothing with
    this text.
  - Only `exit 1` and nothing else: the overlap check found a `run_all` process. Wait, then run the line again.

- [ ] **Step 3: Owner gate: the six owner acts and the daily-task change (then stop)**

  Send the owner one message with three parts, then end the turn and wait. Change nothing before an explicit yes.

  Part 1, the owner acts of E1 spec 12, verbatim (contract 19), introduced by the sentence "These are yours; I
  perform none of them. Main-spec owner acts 1 and 2 (your signing key, then the signed code hash) come before act
  5.":

  > 1. **Upbit key:** issue a key with 자산조회, 주문조회, 출금조회 and 입금조회 only, never 주문하기, 출금하기 or 포켓관리;
  >    register your PC's public IPv4 address; put `UPBIT_ACCESS_KEY` and `UPBIT_SECRET_KEY` in `.env`; note in the
  >    owner's own records which permissions you ticked.
  > 2. **OKX key:** create an API key with the Read permission only, bind your IP, and put `OKX_API_KEY`,
  >    `OKX_API_SECRET` and `OKX_API_PASSPHRASE` in `.env`.
  > 3. **KIS:** nothing new; E1 uses the existing `KIS_APP_KEY`, `KIS_APP_SECRET`, `KIS_ACCOUNT_8` and `KIS_ACCOUNT_PD`.
  > 4. **Task Scheduler:** create a task "TRADEGEN E1 poller", trigger "At log on" of your user, action
  >    `C:\Users\whydi\OneDrive\Desktop\TRADEGEN\.venv\Scripts\python.exe -m execution.poll`, start in
  >    `C:\Users\whydi\OneDrive\Desktop\TRADEGEN`, "Run only when user is logged on", and on the Settings tab untick
  >    "Stop the task if it runs longer than 3 days". Stopping it is one click in Task Scheduler.
  > 5. **Signer:** re-verify your signer copy against the repo's after this change (read the diff, re-hash, re-record),
  >    then sign the code hash as before (owner act 2 of the main spec).
  > 6. **Daily task:** approve the change to `tradegen-compliance-daily`'s prompt so it also sends E1's unsent alerts.

  Then the loss-alarm paragraph of Step 5 item 5, in its exact words (E1 has not polled yet, so all three alarms
  are off).

  Part 1 ends with: "When you tell me in chat that keys are in `.env`, I run one live read-only
  `python -m execution.poll --once` and report its summary only. It reads Upbit and OKX when their keys are there,
  and KIS only once the code is signed."

  Part 2, for act 6: the full text of `<S>/e1_daily_prompt.txt` in a fenced block (say that the Asia/Seoul date of
  the yes replaces `<the date of the owner's yes>`), then the 37 lines that Step 2 printed, unchanged, in a second
  fenced block. Never replace either with a prose summary.

  Part 3, the question, exactly:

  > Change the daily task `tradegen-compliance-daily` to the prompt above (owner act 6)? After its four compliance
  > steps it adds step 5: it runs `python -m execution.poll --pending`, which reads `~/.tradegen/execution/alerts.jsonl`
  > on this PC and makes no network call; when E1 has unsent red or amber alerts, it sends you their fixed text on
  > the same two channels (the iOS push, then the email to `sapientia@korea.ac.kr` only) and marks them sent with
  > `--mark-sent`. It never runs `--once` or the poller and never sends to anyone else. Step 2's `"send": false`
  > now goes on to step 5 instead of stopping, the first paragraph records today's approval of step 5, and the only
  > new files it may change are `~/.tradegen/execution/alerts.jsonl`, its `.lock` and the temporary file
  > `--mark-sent` writes. Step 5 needs `execution/poll.py` in the checked-out branch: on a checkout without it the
  > task sends "TRADEGEN E1: the pending-alert step failed" once a day until E1 is merged. Yes or no?

  End the message with: "The real odds are unchanged by E1: no plan without a real edge that keeps the floor can beat
  about 1 in 1,000 (1 in 2,000 with the floor at half the stake), and the research estimates the practical chance of
  1,000x in a month at 0.01% or less. This is not legal or investment advice; I am not a licensed advisor."

  If Step 2 printed `already the approved prompt, dated <date>`, leave out Parts 2 and 3. Say instead that the live
  prompt already holds step 5 dated `<date>`, quote the helper's line, and ask exactly "Did you approve this on
  `<date>`?". Act 6 counts as approved, here and in Step 8's notes, only on the owner's yes in chat, and Step 4 is
  then skipped. On a no: change nothing, then stop and rule, since reverting the prompt is its own change that needs
  its own yes.

- [ ] **Step 4: Only on an explicit yes: change the daily task, then verify it**

  1. Anything but an explicit yes in chat changes nothing. If the owner asks for other wording, that is a new
     contract 18 text: stop and rule (redraft the prompt, the helper's pins and this step), then show the new computed
     diff and ask again.
  2. On a yes: `<DATE>` is the Asia/Seoul date of the yes as `YYYY-MM-DD`, printed right after the yes by
     `.venv/Scripts/python.exe -I -c "import datetime, zoneinfo; print(datetime.datetime.now(zoneinfo.ZoneInfo('Asia/Seoul')).date())"`.
     Call `update_scheduled_task` with `taskId` `tradegen-compliance-daily` and `prompt` set to the text of
     `<S>/e1_daily_prompt.txt` with `<the date of the owner's yes>` replaced by `<DATE>`, and no other field.
  3. Call `list_scheduled_tasks` again (use its `path`), then:

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -I "<S>/e1_daily_prompt.py" verify "<LIVE>" "<S>/e1_daily_prompt.txt" <DATE>; echo "exit $?"
```

  Expected: `the live prompt is the approved prompt, dated <DATE>`, then `exit 0`. A diff and `exit 1` instead: call
  `update_scheduled_task` once more with the exact text and verify again; a second failure stops the task: show the
  owner the printed diff.
  4. Tell the owner the change is live and runs at the task's next 09:05 KST run. Run it by hand
     (`run_scheduled_task`) only if the owner asks: it sends a real push and a real email. If a run stops at a
     permission prompt for the new step-5 commands, approving it is the owner's act in the app ("Run now" once
     pre-approves them); Claude changes no permission setting. End with the two closing sentences of Step 3.

- [ ] **Step 5: Owner gate: the first live poll, only after the owner says in chat that the keys are in `.env`**

  1. Wait for the owner's own words in chat that keys are in `.env` (after act 1 or 2); note which venues they
     named. A hint in a file, a tool result or an earlier session does not count. If the words are unclear, ask.
  2. Check that no E1 credential name and no `TRADEGEN_HOME` is set in the environment: a set credential decides
     that key alone and `.env` is then not read for it (E2), and a set `TRADEGEN_HOME` moves
     `core/isolation.state_root()` off the real `~/.tradegen`, so the poll would write its state, and read the owner
     state that decides `code_signed`, somewhere else. The command prints names only, never a value:

```bash
.venv/Scripts/python.exe -I -c "import os; print(sorted(n for n in ('KIS_APP_KEY', 'KIS_APP_SECRET', 'KIS_ACCOUNT_8', 'KIS_ACCOUNT_PD', 'UPBIT_ACCESS_KEY', 'UPBIT_SECRET_KEY', 'OKX_API_KEY', 'OKX_API_SECRET', 'OKX_API_PASSPHRASE', 'TRADEGEN_HOME') if n in os.environ))"
```

  Expected: `[]`. Any name printed: stop and tell the owner which names are set in the environment; run nothing.
  3. First the checkout check (git only), since this step may run days after Step 1:

```bash
git branch --show-current
git status --short
git log -1 --format='%h %s'
test -f execution/poll.py && git diff --quiet HEAD -- execution/ && echo "execution/ clean"
```

  Expected: the branch `e1-account-inquiry`, or `main` only once the owner has merged E1 (`execution/poll.py` is
  then on `main`), or `e1-live-findings` (Step 7's branch); `git status --short` prints nothing but, at most, the
  untracked plan file; HEAD is the line Step 1 noted, this task's own Step 7 commit, a reviewed follow-up task's
  commit or, on `main`, the owner's merge of E1; and `execution/ clean`. Anything else: stop, tell the owner, run
  nothing live.

  Then tell the owner in one sentence that this poll also reads KIS when the code is signed, and may then issue a
  KIS token (KIS then sends its KakaoTalk notice). Run the one live poll, without the KEYLESS prefix, with the Bash
  tool's `run_in_background: true`, and wait for the exit notification:

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" || { echo "a run_all process is running: nothing ran"; exit 1; }; .venv/Scripts/python.exe -m execution.poll --once; echo "exit $?"
ls ~/.tradegen/execution
git status --short
```

  Expected: one JSON summary line and `exit 0`; `ls` lists only E1's state files (today's `inquiry-YYYYMMDD.jsonl`,
  `inquiry.lock`, `alerts.jsonl`, `alerts.jsonl.lock`, `poll.lock`, and `evidence.jsonl` with its `.lock` when KIS
  was read); `git status --short` prints nothing but, at most, the untracked plan file (the poll writes nothing in
  the repo). Other outputs:
  - `a run_all process is running: nothing ran`: the overlap check found a `run_all` process. Nothing ran; wait,
    then run the block again.
  - `another E1 poller holds poll.lock; exiting` and `exit 0`: the owner's logon poller (act 4) is already
    polling, and this command polled nothing (E1R2-1). Tell the owner; never stop the poller; skip to Step 8.
  - `{"crash": "<TypeName>", "at": "<file>:<line>"}` and `exit 4`: a bug. One crash line: the poller wrote and
    toasted the fresh OUTAGE_CRASH rows. Two crash lines: it could not write them and toasted CRASH_UNLOGGED instead
    (E40). Report every line, run nothing more, and go to Step 7 (a crash finding, one ledger line quoting every
    crash line).
  4. Read each venue whose `venues` value is `"error"` by its text in `errors`, top row first:

| Error text | Meaning | What Claude does |
|---|---|---|
| `keys missing: <NAME>` | that venue's keys are not in `.env` (E31) | expected, not a fault: one amber KEY_MISSING toast today; `not_set` lists `<Venue>: keys not in .env` |
| `code not signed` (KIS) | the code hash is not signed yet, so KIS sent nothing, no token included (E42, E1R2-9) | expected, not a fault: one amber KIS_UNSIGNED toast today; the first live KIS read waits for Step 6 |
| `okx self-check failed: <names>` with `autoLoan` in `<names>` and `acctLv` not in it | auto-loan is on for a spot-mode key (`acctLv == "1"`; E1R2-6, open issue 6) | stop and ask the owner; also tell them what every other name in `<names>` means, as the next row does; never loosen the check; Step 7 (an E1R2-6 finding) |
| `okx self-check failed: <names>`, any other set | the check working as designed: the key is not Read-only (`perm`), the account is not spot mode (`acctLv`), spot borrowing is on (`enableSpotBorrow`) or no IP is bound (`ip`); one red KEY_OKX_SELF_CHECK toast | tell the owner which settings `<names>` names and that owner act 2 asks for a Read-only key bound to an IP; change nothing |
| `kis /uapi/overseas-stock/<path>: HTTP <status>` with a status other than 401 and 403, with or without a code, the code not in `AUTH_CODES["kis"]` | the domestic calls passed and an overseas inquiry was refused: most likely the overseas stock service (해외주식 서비스) is not enabled on the account (E1R2-7, open issue 7) | stop and ask the owner whether it is enabled; never drop or loosen the overseas calls; Step 7 (an E1R2-7 finding) |
| `<venue>: <path>: field <name>` or `<venue>: <path>: <TypeName>` | the live answer does not have the shape the fixtures assumed, a field marked `[assumed]` included; the venue failed closed (E1R2-5, open issue 5) | report it; Step 7 (an E1R2-5 finding); the fix is a follow-up task |
| `kis: KIS account number is not 8 + 2 digits` | `KIS_ACCOUNT_8` or `KIS_ACCOUNT_PD` in `.env` is not 8 and 2 digits | tell the owner; Claude never opens `.env` |
| `<venue> <path>: HTTP 401` or `HTTP 403`, or a code in `AUTH_CODES[<venue>]` | the key was refused: a permission not ticked (Upbit `out_of_scope`), the IP not registered or bound (`no_authorization_ip`, OKX 50110), an expired or wrong key | tell the owner which act covers it (1 for Upbit, 2 for OKX; for KIS, the existing key of act 3 was refused); change nothing |
| `unknown venue <name>`, `<venue>: <method> <path> is not on the E1 allowlist`, `<venue>: <method> is not GET`, `kis: the token POST takes no parameters`, `kis: <path> needs its pinned TR id ending in R, got <id>`, `<venue>: a TR id belongs only to a KIS inquiry`, `<venue>: parameter <key> is not plain` | transport refused E1's own request (`InquiryRefused`, before any key was read): only a bug in E1's code gives these | report it; Step 7 (a refusal finding); the fix is a follow-up task |
| anything else (`HTTP 429` or `5xx`, `ConnectionError`, `ReadTimeout`, a refusal over the OKX clock, `kis: no token may be issued yet; KIS skipped this poll`) | a venue or network fault, or this PC's clock | report it; run another `--once` only when the owner asks in chat |

  Expected, not faults, besides the first two rows: `not_set` also lists the FLOOR, DAILY_LOSS and OKX_CAP items
  (`not set` until the owner's signed limits exist, or `no live positions` while a venue is not ok) and
  `ADDRESS_LIST: owner log not OK` while the owner log is not OK; those checks are skipped and recorded once a day,
  never failed (E43). `alerts` counts this poll's fresh red and amber alerts, each also a Windows toast.
  5. Report to the owner in this form, filled from the summary line only (counts for ok venues only):

  > First live read-only poll at `<utc>` (`python -m execution.poll --once`, exit 0): KIS `<ok, or error: "<text>">`,
  > Upbit `<ok, or error: "<text>">`, OKX `<ok, or error: "<text>">`. Counts: `<venue>`: `<holdings>` holdings, `<open_orders>` open orders, `<fills>` fills,
  > `<deposits>` deposits, `<withdrawals>` withdrawals, `<addresses>` registered withdrawal addresses. Evidence
  > records: `<n, or broken>`. New red or amber alerts: `<n>` (each also shown as a Windows toast). Not set:
  > `<the not_set items>`. It wrote the real `~/.tradegen/execution` files (`<the names ls printed>`)
  > `<when KIS was sent to: and may have refreshed ~/.tradegen/kis_token.json, so KIS may have sent its KakaoTalk
  > issuance notice | when KIS shows keys missing or code not signed: and sent nothing to KIS, so no KIS token was
  > issued>`, and it may have shown Windows toasts.

  When `not_set` holds a FLOOR, DAILY_LOSS or OKX_CAP item, add this paragraph right after the `Not set:` sentence,
  in these words (the loss-alarm paragraph):

  > E1's three loss alarms are off right now. FLOOR warns when your live total across KIS, Upbit and OKX is at or
  > below your total-loss floor. DAILY_LOSS warns when that total falls by at least your daily loss limit since the
  > day's first poll. OKX_CAP warns when OKX holds more than your okx_equity_share cap. They run only when your signed
  > limits exist and all three venues read ok in the same poll, no more than 15 minutes old. "not set" means your
  > signed limits do not exist yet (or the owner log is not OK). "no live positions" means a venue was not read: KIS
  > stays unread until you sign the code, and a venue without keys keeps them off. While they are off, nothing warns
  > you about losses; the daily not-set record stays on this PC and is never sent. They turn on by themselves once
  > those conditions hold. E1 only alerts; it never sells or halts.

  Then one plain sentence per error, from the table, and last the closing sentences of Step 3 (the real odds, and
  "This is not legal or investment advice; I am not a licensed advisor."). Never add a balance, an address, a key or
  a token.
  6. Any later `--once` (for example after the owner adds the other venue's keys) runs only when the owner asks for
     it in chat, under this step's rules.

- [ ] **Step 6: Owner gate: the first live KIS read, only after the owner says in chat that the code is signed**

  Until the owner has done main-spec owner acts 1 and 2 and E1 owner act 5, every poll shows KIS
  `code not signed` (E42). When the owner says in chat that the code is signed:
  - If Step 5's poll has not run yet, Step 5's gate still holds (contract 19): ask the owner whether keys are in
    `.env` (Upbit and OKX show `keys missing` until theirs are), and go on only after they say in chat that they are.
  - Tell them in one sentence (it replaces Step 5's) that this poll sends the KIS inquiry and may issue a KIS token
    (KIS then sends its KakaoTalk notice), then run Step 5's items 2 and 3 again, unchanged (the checkout check
    first, the poll with `run_in_background: true`), and read and report the result by Step 5's items 4 and 5.
  - If KIS still shows `code not signed`: when `not_set` holds `ADDRESS_LIST: owner log not OK`, tell the owner that
    the owner log is not OK, so no code counts as signed (main-spec owner acts 1 and 2); otherwise tell them that the
    signed hash does not cover the code on disk (act 5: re-verify the signer copy, then sign again). Run nothing
    more.

  The E1R2-7 row of the table can first show here.

- [ ] **Step 7: Only when Step 5 or Step 6 stopped on a finding: the ledger and its commit**

  Skip this step when no poll stopped on an E1R2-5, E1R2-6 or E1R2-7 finding, a refusal of E1's own request or a
  crash. Otherwise run Step 5's checkout check first. On `main` (E1 merged) never commit there: run
  `git switch -c e1-live-findings` first (`git switch e1-live-findings` when that branch exists already). Then
  re-read the ledger (the DRIFT RULE, contract 0.6). Task 13 left four sections in order, `## Drift rulings`,
  `## Deferred minors`, `## Round-2 rulings as applied` and `## Runs`, each heading once, and the lines go at the
  end of the "Deferred minors" section, after whatever Tasks 1 to 13 wrote there, so the anchor is the round-2
  heading (a missing heading: stop and rule). With the Edit tool (LF), old text:

```text
## Round-2 rulings as applied
```

  New text: one line for each finding that occurred, in the order they occurred, filled from the summary and the
  owner's words, then one blank line, then the heading. Write the owner's answer without any balance, address,
  account number, key or token (the repo is public, G3-3). All five forms:

```text
- Task 14 (E1R2-5): the live --once at <utc> failed <venue> closed with "<the error text, exactly as printed>"; the fixture field does not match the live answer; fix it in a follow-up task under the plan's rules (the corrected fixture's failing test first, then the parser; the owner signs the new code hash).
- Task 14 (E1R2-6): the live --once at <utc> failed the OKX self-check with "<the error text>" (autoLoan true, acctLv 1: a spot-mode key); the check stays strict; asked the owner on <YYYY-MM-DD>; the owner's answer: <the answer in one line, or "not yet">.
- Task 14 (E1R2-7): the live --once at <utc> failed KIS with "<the error text>" (an overseas inquiry); asked the owner on <YYYY-MM-DD> whether the overseas stock service is enabled; the owner's answer: <the answer in one line, or "not yet">.
- Task 14 (refusal): the live --once at <utc> failed <venue> with "<the error text>", transport's refusal of E1's own request (a bug); fix it in a follow-up task under the plan's rules.
- Task 14 (crash): the live --once at <utc> printed <every crash line, exactly as printed> and exited 4; fix it in a follow-up task under the plan's rules.

## Round-2 rulings as applied
```

  Then:

```bash
git status --short
git add docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
```

  `git status --short` lists ` M docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md` and
  nothing else but, at most, the untracked plan file (never staged). The two stat outputs must be identical, each
  `1 file changed, <k+1> insertions(+)`, `<k>` the number of finding lines and the 1 the blank line. In the trailer,
  replace `<the committing model>` with the name of the model that writes this commit, for example
  `Claude Opus 5.5` (contract 0.4):

```bash
git commit -m "docs(ledger): record the first live E1 poll's findings" -m "Task 14: what the owner-gated first live --once showed that waits on the owner or a follow-up task (E1R2-5 to E1R2-7, a refusal or a crash); no code changed." -m "Co-Authored-By: <the committing model> <noreply@anthropic.com>"
git log --oneline -1
git status --short
```

  Expected: the new commit on the branch the checkout check named (`e1-live-findings` in place of `main`), and
  `git status --short` prints nothing but, at most, the untracked plan file. On `e1-account-inquiry` (E1 not merged
  yet) the controller pushes it with `git push` after review (G3-3). On `e1-live-findings` (E1 already merged) G3-3
  does not cover the push: leave the commit local, tell the owner the branch and the commit subject, and push it
  (`git push -u origin e1-live-findings`) and open its pull request only after the owner says yes in chat. No
  subagent pushes. When the owner answers an open question later, run the checkout check, change that line's
  `not yet` to the answer the same way (the two stats then read `1 file changed, 1 insertion(+), 1 deletion(-)`) and
  commit it alone with the same commands; the same rule decides its push (on `e1-account-inquiry` the controller
  pushes after review; on `e1-live-findings` only after the owner's yes in chat, `git push` once the branch is on
  the remote).

- [ ] **Step 8: Memory and hand-over notes**

  Fill every angle-bracketed field from this session: the short sha of `git log --oneline -1`, the totals line that
  Task 13 wrote under `## Runs`, the execution suite's count (the `<n> PASS` of that line's `execution <n> PASS`: 228
  by the drafts; under G3-1 another count with 0 failed passes, and the ledger gives the reason), the push and merge
  state, and the outcomes of Steps 3 to 7 (a step that has not happened says so). The controller opens the plan's
  one pull request after this task's first-session review (G3-3); until then its field says `not opened yet`. Never
  write a balance, an address, a key or a token. If a file already holds the E1 block (a later session), edit its
  lines in place, the old text being the line that holds the field that changed, and append nothing. Otherwise each
  anchor is the file's line as read now; if another plan's final task appended after it, use the file's last line
  as you read it (the DRIFT RULE). Keep each file's line endings (the Edit tool does).

  1. `plans-2026-10-24-decisions.md`. Old text (its last line on 2026-10-28):

```text
**How to apply:** do not re-ask; departures from spec rev 3.2 (layout, review_by) go into the plans as recorded rulings and into spec rev 3.3.
```

  New text:

```text
**How to apply:** do not re-ask; departures from spec rev 3.2 (layout, review_by) go into the plans as recorded rulings and into spec rev 3.3.

**E1 built (<YYYY-MM-DD>):** branch `e1-account-inquiry`, head `<short sha>`, <pushed, or not pushed yet>; <not merged, or merged by the owner on YYYY-MM-DD>; full run `<the Total line of Task 13's run>`; execution suite `<n> PASS`. `python -m execution.poll` reads KIS, Upbit and OKX through one GET-only transport with frozen allowlists and only alerts; KIS sends nothing until the owner signs the code hash (E1R2-9). Daily task step 5: <approved on YYYY-MM-DD, or not approved yet>. First live --once: <not run yet, or run at <utc>: KIS, Upbit and OKX each ok or its error text>.
- Owner acts still open (E1 spec 12): <the open act numbers of 1-6>; main-spec owner acts 1 and 2 (signing key, signed code hash) come before act 5 and gate the first KIS read.
- Waiting on a live answer: E1R2-5 (a live field mismatch, `[assumed]` fields included, fails that venue closed; a follow-up task fixes it), E1R2-6 (OKX autoLoan true on a spot-mode key: stop and ask), E1R2-7 (KIS overseas service not enabled: stop and ask). <Any Step 7 ledger line, in one clause each, or "none seen yet">.
- For E1 spec rev 2: E1R2-3 (evidence written on a met change and as a daily heartbeat), E1R2-4 (daily inquiry-YYYYMMDD.jsonl files, never deleted), E1R2-9 (KIS only under signed code).
```

  2. `MEMORY.md`. Old text:

```text
- [2026-10-24 plan decisions](plans-2026-10-24-decisions.md) — E1-E3 split; E1 keys/polling/D16 auto-lift/execution/ signed; odds "everything injected", review_by, venues, SPECIAL_REGIME
```

  New text:

```text
- [2026-10-24 plan decisions](plans-2026-10-24-decisions.md) — E1-E3 split; E1 keys/polling/D16 auto-lift/execution/ signed; odds "everything injected", review_by, venues, SPECIAL_REGIME; E1 built on branch e1-account-inquiry (owner acts, live --once state)
```

  3. `tradegen-phase-a.md`. Old text (its last line on 2026-10-28):

```text
- Still owed: GPT's check after 2026-10-30 14:40, owner acts 1-6, and then the odds plan.
```

  New text:

```text
- Still owed: GPT's check after 2026-10-30 14:40, owner acts 1-6, and then the odds plan.

E1 account inquiry built, <YYYY-MM-DD> (TRADEGEN session):
- Branch `e1-account-inquiry`, head `<short sha>`, <pushed to origin, or not pushed yet> (the controller pushes after each reviewed task, round-3 ruling G3-3); <not merged, or merged by the owner on YYYY-MM-DD>; pull request `<its URL, or "not opened yet">`. Full run `<the Total line of Task 13's run>`; execution suite `<n> PASS`. The ledger is `docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md`.
- E1 only reads and alerts: one GET-only transport with frozen allowlists, KIS sent nothing until the code hash is signed (E1R2-9), toasts at once and the daily task for push and email.
- Daily task step 5 (owner act 6): <approved on YYYY-MM-DD, or not approved yet>. First live --once: <not run yet, or run at <utc>: venues and ok or error only>.
- Owner acts still open: <the open act numbers of E1 spec 12>, plus main-spec acts 1 and 2 before act 5.
- Waiting on a live answer: E1R2-5, E1R2-6, E1R2-7 (<the Step 7 lines in one clause each, or "none seen yet">). For the owner's E1 spec rev 2: E1R2-3, E1R2-4, E1R2-9.
```

  These three files are outside the repo, so nothing is committed. Afterwards, in the repo, `git status --short`
  prints nothing but, at most, the untracked plan file.
