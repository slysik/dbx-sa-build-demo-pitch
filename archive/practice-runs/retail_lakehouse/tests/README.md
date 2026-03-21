# Tests

## Planned

- [ ] Unit tests for Bronze generation logic (schema validation, FK integrity)
- [ ] Integration tests for Silver dedup correctness
- [ ] Gold aggregation validation (sum reconciliation Bronze → Gold)

## Run

```bash
pytest tests/ -v
```

In production, these run in CI on every PR before `bundle deploy`.
