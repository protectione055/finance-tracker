#!/usr/bin/env bash
set -euo pipefail

DAYS=7
TOP=10
SOURCE="qqmail"
DRY_RUN="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --days)
      DAYS="$2"
      shift 2
      ;;
    --top)
      TOP="$2"
      shift 2
      ;;
    --source)
      SOURCE="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN="true"
      shift
      ;;
    *)
      echo "Unknown arg: $1"
      exit 2
      ;;
  esac
done

SYNC_ARGS=(python3 cli.py sync run --source "$SOURCE" --days "$DAYS")
if [[ "$DRY_RUN" == "true" ]]; then
  SYNC_ARGS+=(--dry-run)
fi

echo "[1/4] Sync..."
"${SYNC_ARGS[@]}"
echo "[2/4] Sync status..."
python3 cli.py sync status
echo "[3/4] Latest transactions..."
python3 cli.py tx list --limit 20
echo "[4/4] Spending report..."
python3 scripts/spending_report.py --db ./data/finance.db --days "$DAYS" --top "$TOP"
