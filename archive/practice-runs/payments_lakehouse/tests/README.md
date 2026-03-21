# Tests

## Planned

- [ ] Unit tests for Bronze generation logic (schema validation, FK integrity)
- [ ] CHECK constraint enforcement tests (invalid amount, status)
- [ ] Row count validation (expected vs actual)
- [ ] Distribution tests (status/currency percentages within tolerance)

## Run

```bash
pytest tests/ -v
```

In production, these run in CI on every PR before `bundle deploy`.
