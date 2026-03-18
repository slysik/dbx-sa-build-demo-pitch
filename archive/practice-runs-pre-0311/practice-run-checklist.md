# Practice Run Checklist

End-to-end validation for interview readiness. Run with `just practice-run retail` or `just practice-run media`.

---

## Pre-Flight
- [ ] `just interview-check` passes (all green)
- [ ] `just dbx-auth` shows valid token
- [ ] Workspace has `dbx_weg` catalog with bronze/silver/gold schemas

---

## Run 1: Retail Vertical

### Execution
- [ ] 1. Run `just practice-run retail` (or `just interview` with a retail prompt)
- [ ] 2. Verify: PySpark data gen uses `spark.range()` (NOT pandas-only, NOT SQL-only)
- [ ] 3. Verify: ~100k rows generated (check `df.count()` output)
- [ ] 4. Verify: Narration comments present (TALK/SCALING/DW-BRIDGE in every stage)
- [ ] 5. Verify: Orange ANSI highlighting on narration lines in terminal
- [ ] 6. Verify: No "FinServ" or "finserv" language in generated code
- [ ] 7. Verify: All stage gates pass (Bronze -> Silver -> Gold -> Dashboard -> Validation)
- [ ] 8. Verify: Dashboard deploys and all widgets show data
- [ ] 9. Verify: Validation harness passes (counts, uniqueness, rules, pruning)
- [ ] 10. Time check: total pipeline < 45 minutes?

### Scaling Discussion Dry Run
For each stage, practice saying aloud:
- [ ] **Data Gen**: "spark.range() distributes across executors. Like nzload across SPUs."
- [ ] **Bronze**: "Append-only Delta writes are embarrassingly parallel. Liquid Clustering replaces distribution keys."
- [ ] **Silver MERGE**: "ROW_NUMBER shuffle is the expensive op. CLUSTER BY pre-sorts for merge-join."
- [ ] **Gold**: "Delete-window touches <1% at scale. Same correctness as TRUNCATE+reload, 100x less I/O."
- [ ] **Dashboard**: "Pre-aggregated Gold means queries scan KB not TB."

### Issues Found
| Issue | Fix Applied | Captured in lessons.md? |
|-------|------------|------------------------|
| | | |

---

## Run 2: Media Vertical

### Execution
- [ ] 1. Run `just practice-run media` (or `just interview` with a media prompt)
- [ ] 2. Verify: Entity names are media-specific (streams, users, content -- NOT orders/customers)
- [ ] 3. Verify: PySpark data gen uses `spark.range()` with media entity columns
- [ ] 4. Verify: ~100k rows generated
- [ ] 5. Verify: Narration comments present and orange-highlighted
- [ ] 6. Verify: No retail or FinServ language in generated code
- [ ] 7. Verify: All stage gates pass
- [ ] 8. Verify: Dashboard deploys with media-appropriate widgets
- [ ] 9. Time check: total pipeline < 45 minutes?

### Vertical Swap Validation
- [ ] Entity names correct for media (stream_id, user_id, content_id, etc.)
- [ ] Measures correct (watch_time, engagement_score, NOT revenue/basket_size)
- [ ] Discovery questions appropriate for media

### Issues Found
| Issue | Fix Applied | Captured in lessons.md? |
|-------|------------|------------------------|
| | | |

---

## Post-Run Checks

- [ ] No MLflow/model code generated in either run
- [ ] `vertical-quick-swap.md` entity maps were sufficient for both verticals
- [ ] TALK comments are conversational and read naturally aloud
- [ ] SCALING comments include specific numbers ("1M rows", "<1%", "100x")
- [ ] DW-BRIDGE comments reference Netezza/traditional DW specifically

---

## Final Sign-Off

| Check | Status |
|-------|--------|
| Retail pipeline completes < 45 min | |
| Media pipeline completes < 45 min | |
| Narration comments present and orange | |
| No FinServ language anywhere | |
| Scaling discussion rehearsed | |
| All lessons captured in tasks/lessons.md | |
| Ready for interview? | |
