---
name: finance-tracker-cli
description: Operate and troubleshoot the Finance Tracker CLI in this repository, including config setup, QQMail IMAP sync runs, scheduler commands, account/transaction queries, and SQLite spending analytics. Use when users ask to run finance tracker commands, debug sync/config issues, inspect data in data/finance.db, or track spending flows through cli.py.
---

# Finance Tracker CLI+Tracker

## Quick Start

1. Prepare runtime and config.
```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp config/config.example.yaml config/config.yaml
```
2. Validate configuration.
```bash
python3 cli.py config show
```
3. Run sync (dry-run first).
```bash
python3 cli.py sync run --source qqmail --days 7 --dry-run
python3 cli.py sync run --source qqmail --days 7
```
4. Inspect data and spending report.
```bash
python3 cli.py tx list --limit 50
python3 skills/finance-tracker-cli/scripts/spending_report.py --db ./data/finance.db --days 30 --top 10
```

## Workflow

1. Identify task type: setup, sync, query, schedule, or troubleshooting.
2. Check state with `python3 cli.py config show` and `python3 cli.py sync status`.
3. Use narrow commands first (`--dry-run`, `--days`, `--limit`, `--account-id`).
4. Execute requested CLI task from `cli.py`.
5. Generate user-facing spending insights with `scripts/spending_report.py`.
6. If output is wrong, inspect `src/services/sync_manager.py`, `src/parsers/cmb_email_parser.py`, and `src/storage/database.py`.

## Command Playbook

```bash
python3 cli.py sync status
python3 cli.py config get database.sqlite.path
python3 cli.py account list --limit 50
python3 cli.py tx list --account-id 8551 --type income --limit 50
python3 cli.py schedule start --interval 60
python3 skills/finance-tracker-cli/scripts/spending_report.py --db ./data/finance.db --days 30 --top 10
```

## References

Load `references/command-reference.md` for extended commands, validation routine, and SQL checks.
