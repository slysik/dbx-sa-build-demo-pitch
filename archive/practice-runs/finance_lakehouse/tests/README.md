# Tests

## Planned (Production Hardening)

- [ ] Bronze schema validation — assert column types match StructType spec
- [ ] Referential integrity — no orphaned `customer_id` or `merchant_id` in Silver
- [ ] Risk score bounds — no scores outside 0–100
- [ ] Dedup assertion — Silver `txn_id` is unique
- [ ] Gold reconciliation — `SUM(silver.amount)` == `SUM(gold_daily.total_amount)`

## Run

```bash
pytest tests/ -v
```

In production these run in CI on every PR before `databricks bundle deploy`.
