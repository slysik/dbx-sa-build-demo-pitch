Build a real-time payment authorization pipeline for a retail bank.
Transactions arrive with possible duplicates (same txn_id, different timestamps).
Deduplicate in Silver, aggregate daily volumes by merchant in Gold.
Include fraud velocity features (txn count per account in last 1 hour).

CONSTRAINTS:
- Generate ~1000 synthetic records (functional test, not volume)
- Keep serverless compute costs minimal
