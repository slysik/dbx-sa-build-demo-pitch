# Tests

## Planned

- [ ] Unit tests for Bronze CDC generation (correct INSERT/UPDATE/DELETE ratios)
- [ ] Integration tests for APPLY CHANGES correctness (99K rows, updated values, no deleted rows)
- [ ] Gold aggregation validation (sum reconciliation Silver → Gold)
- [ ] Metric view query validation (MEASURE() returns correct aggregates)

## Run

```bash
pytest tests/ -v
```

In production, these run in CI on every PR before `bundle deploy`.
