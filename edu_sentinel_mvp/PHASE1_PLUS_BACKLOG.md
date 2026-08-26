# EDU Sentinel Phase 1+ Backlog

This backlog continues from the Phase 1 Executive MVP and turns the demo into a
pilot-ready foundation.

## Completed in This Phase 1+ Pass

- Added governance reference tables for KPI definitions, policy programs, data sources and audit logs.
- Added Executive data masking for `student_id` and alert evidence references.
- Added Policy Intelligence view for coverage gaps, program registry and SLA risk.
- Expanded Admin & Governance with KPI dictionary, source lineage, policy registry and audit trail.
- Added `openapi_phase1_plus.yaml` as the first API contract draft for service extraction.

## Next Engineering Epics

1. Service extraction
   - Move SQLite access behind API services that match `openapi_phase1_plus.yaml`.
   - Add request-level RBAC, masking and audit middleware.
   - Keep Streamlit as demo UI until the React/Next.js shell is ready.

2. Data model and migrations
   - Introduce explicit `areas`, `schools`, `indicators`, `risk_assessments`, `alerts`, `case_actions`, `policy_programs`, `data_sources` tables.
   - Replace ad hoc schema changes with versioned migrations.
   - Add uniqueness checks for `student_id + period + source_id`.

3. Map and drill-down
   - Add Thailand province/district GeoJSON or PostGIS-backed boundaries.
   - Support country > province > district > school navigation from one interaction path.
   - Persist selected area context when opening alert detail.

4. Alert intelligence
   - Version rule thresholds in a table instead of constants.
   - Add trend and SLA breach alert types.
   - Store formula inputs and driver values as structured JSON for audit review.

5. AI guardrails
   - Turn the offline summary into an `/ai/executive-summary` endpoint.
   - Log prompt version, retrieved evidence and unsupported-claim checks.
   - Add evaluation cases for citation errors, sensitive leakage and rights-decision refusal.

6. Quality and security
   - Add unit tests for risk scoring, schema normalization, masking, RBAC and audit logging.
   - Add smoke tests for the executive demo path.
   - Replace demo passwords and add environment-based secret handling before pilot use.

## Pilot Readiness Checklist

- Every KPI has source, definition, period, denominator, aggregation level and data quality flag.
- Every alert has severity, priority score, trigger, drivers, evidence, rule/model version and SLA.
- Every action from an alert records owner, due date, status, outcome and audit entry.
- Executive role sees policy-level insight without direct student identifiers.
- Admin can inspect data source lineage, KPI definitions, policy registry and audit trail.
