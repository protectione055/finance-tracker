from datetime import datetime
from decimal import Decimal
from pathlib import Path

from src.storage.database import TransactionRepository
from src.models.transaction import RawTransaction, Counterparty, TransactionType


def test_transaction_repository_save_and_dedupe(tmp_path: Path):
    db_path = tmp_path / "finance.db"
    repo = TransactionRepository(db_path=str(db_path))

    tx = RawTransaction(
        raw_id="raw-1",
        source_type="cmb_email",
        source_account="test@example.com",
        transaction_time=datetime(2026, 2, 21, 19, 25),
        account_id="8551",
        transaction_type=TransactionType.CONSUMPTION,
        amount=Decimal("3.00"),
        counterparty=Counterparty(name="测试商户", type="merchant"),
    )

    saved, message = repo.save_transaction(tx)
    assert saved is True
    assert message == "saved"

    saved2, message2 = repo.save_transaction(tx)
    assert saved2 is False
    assert message2 == "duplicate"

    # current_balance should be updated (consumption => negative delta)
    with repo._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT current_balance FROM accounts WHERE account_id = ?",
            ("8551",),
        )
        row = cursor.fetchone()
        assert row is not None
        assert Decimal(str(row[0])) == Decimal("-3.00")
