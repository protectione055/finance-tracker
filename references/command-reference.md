# Finance Tracker Command Reference

## Fetch

```bash
python3 cli.py sync run --source qqmail --days 7 --dry-run
python3 cli.py sync run --source qqmail --days 7
python3 cli.py sync status
```

## Query

```bash
python3 cli.py account list --limit 50
python3 cli.py tx list --limit 50
python3 cli.py tx list --account-id 8551 --type income --limit 50
```

## Report

```bash
python3 scripts/spending_report.py --db ./data/finance.db --days 30 --top 10
```

## Key Config Paths

- `sources.qqmail.username`
- `sources.qqmail.auth_code`
- `sources.qqmail.account_id`
- `database.sqlite.path`

## Validation

```bash
python3 -m pytest tests/test_cmb_email_parser.py tests/test_transaction_repository.py
```

## SQL Checks

```sql
SELECT account_id, current_balance, last_sync_time
FROM accounts
ORDER BY account_id;
```

```sql
SELECT transaction_time, amount, transaction_type, counterparty_name
FROM transactions
ORDER BY transaction_time DESC
LIMIT 20;
```
