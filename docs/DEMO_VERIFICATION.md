# Demo Verification

Last verified: 2026-04-01

## Purpose

Use this checklist before demos to confirm that the hiring workflow still works end to end after code changes.

## Preconditions

- local stack is running
- coordinator health returns `status=ok`
- queue worker is running
- websocket connection is available from the frontend
- OpenAI credentials are configured if model-backed verification is required

## Demo Checklist

1. Create a new job with the real `POST /jobs/create` flow.
2. Upload at least one `TXT`, one `PDF`, and one `DOCX` resume.
3. Confirm upload APIs return `202 Accepted` with queued results.
4. Confirm `/health` shows the workflow queue moving through `pending` and `running`.
5. Confirm candidates appear in `GET /candidates?job_id=...`.
6. Confirm no candidate remains stuck in `processing` after the queue drains.
7. Confirm `GET /jobs/{job_id}/artifacts` contains intake, skill assessment, screening, and audit artifacts for each candidate.
8. Confirm `GET /stats?job_id=...` returns coherent totals.
9. Confirm review-required state appears in candidate list and detail APIs.
10. Trigger `POST /jobs/{job_id}/rank`.
11. Confirm ranking metadata is persisted without overwriting screening/audit outcomes.
12. Confirm websocket activity updates stream through intake, skill assessment, screening, audit, and workflow completion.

## 2026-04-01 Verification Summary

Verification job:

- `demo-verify-1774976060`

Checked successfully:

- job creation worked
- batch upload worked for `TXT`, `PDF`, and `DOCX`
- queue worker drained all 3 uploads
- 3 candidates were persisted
- 9 workflow artifacts were created before ranking
- ranking completed for 3 candidates
- 3 ranking artifacts were added after rerank
- candidate decision trails included `candidate_ranking_result`
- websocket stream emitted queued, dequeued, intake, screening, audit, and completion events
- OpenAI-backed execution was observed in intake, screening, and audit artifacts

Observed stats:

- `total_candidates=3`
- `shortlisted=1`
- `rejected=2`
- `review_required=3`

Notes:

- the queue and websocket fixes behaved correctly during the live run
- the system is functionally demo-ready
- current code now also persists a skill-assessment artifact per completed candidate workflow, so artifact counts may be higher than this 2026-04-01 snapshot
- fallback extraction and explanation quality are still the most visible product rough edges

## Suggested Re-Test After Future Changes

Re-run this checklist after changes to:

- coordinator queue or websocket logic
- resume parsing
- screening thresholds or review-state logic
- ranking behavior
- frontend candidate loading or live activity behavior
