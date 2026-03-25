# Audit Log Validation Report
**Date:** 2026-04-04 19:22
**Entries Analyzed:** 65

| Level | Count |
|-------|-------|
| ✅ OK | 5 |
| ⚠️ Warning | 1 |
| ❌ Fail | 0 |

## Findings

**✅ [Fields]** All 65 log entries have valid field structures

**⚠️ [Coverage]** Success actions: NONE

**✅ [Coverage]** Denial actions: DENIED_MODEL, DENIED_MODEL_UNKNOWN

**✅ [Integrity]** Observed 25 request_ids with multiple lifecycle events (expected in multi-step flows)

**✅ [Timestamps]** All timestamps in past

**✅ [Immutability]** DB-level immutability probe skipped (no direct DB connection in this validator).

