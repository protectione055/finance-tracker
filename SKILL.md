---
name: finance-tracker
description: Track personal spending flows in this repository using Finance Tracker CLI. Use when users want to configure QQMail IMAP sync, fetch new bank transactions via cli.py, query accounts/transactions from SQLite, or produce spending summaries and trend reports.
---

# Finance Tracker Skill

## Quick Start

1. Prepare environment.
```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```
2. Prepare config.
```bash
cp config/config.example.yaml config/config.yaml
python3 cli.py config show
```
3. Fetch transactions.
```bash
python3 cli.py sync run --source qqmail --days 7 --dry-run
python3 cli.py sync run --source qqmail --days 7
```
4. Query and analyze.
```bash
python3 cli.py account list --limit 50
python3 cli.py tx list --limit 50
python3 scripts/spending_report.py --db ./data/finance.db --days 30 --top 10
```

## Workflow

1. Identify user goal: setup, fetch, query, or troubleshooting.
2. Check state: `python3 cli.py config show` and `python3 cli.py sync status`.
3. Run fetch commands first when data may be stale.
4. Run query commands to answer user questions.
5. Generate spending summary with `scripts/spending_report.py`.
6. Use `references/command-reference.md` when advanced filtering or SQL verification is needed.

## One-shot Flow

Use this when user wants full fetch-and-query in one command:

```bash
bash scripts/fetch_and_query.sh --days 7 --top 10
```
