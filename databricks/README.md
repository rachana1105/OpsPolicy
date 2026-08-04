# OpsPolicy — Analytics Engine (Databricks)

The analytics engine runs **behind** OpsPolicy. Normal users never open
Databricks; they see compliance metrics and simulation results inside the
platform, served through backend APIs. The core operational platform does not
depend on this engine for any synchronous decision.

## Why it's decoupled

Policy evaluation, approvals, provisioning, and revocation must stay fast and
always-available. Analytics is inherently batch and historical, so it sits on
the other side of an export boundary and an `AnalyticsProvider` interface. If
Databricks is down, the platform keeps running and analytics pages simply show a
stale-data or unavailable state.

## Data flow

```
PostgreSQL ──► incremental export (JSON/Parquet + manifest)
           ──► Unity Catalog Volume
           ──► ingestion notebook  ──► Bronze Delta tables
           ──► clean + enrich      ──► Silver Delta tables
           ──► compliance metrics  ──► Gold Delta tables
           ──► backend reads result ──► React analytics pages
```

## Catalog layout

```
opspolicy.bronze     -- raw ingested source records (with lineage columns)
opspolicy.silver     -- deduplicated, normalised, enriched
opspolicy.gold       -- refreshed compliance summary tables
opspolicy.simulation -- historical policy-simulation inputs and results
```

## Notebooks

| Notebook | Purpose |
| --- | --- |
| `00_setup_tables.py` | Create catalog, schemas, and Delta tables |
| `01_ingest_operational_data.py` | Load exported files into Bronze |
| `02_build_compliance_metrics.py` | Bronze → Silver → Gold compliance metrics |
| `03_run_policy_simulation.py` | Evaluate historical requests against a proposed policy |
| `04_publish_results.py` | Publish Gold + simulation results for the backend |

## Jobs

- `jobs/compliance_refresh.yml` — `ingest_exports → clean_and_enrich →
  build_compliance_metrics → publish_gold_tables`
- `jobs/policy_simulation.yml` — `load_simulation_request →
  evaluate_historical_requests → calculate_impact → publish_simulation_result`

## Simulation equivalence

The Databricks simulation must apply the **same deterministic rule logic** as
the synchronous engine, so a proposed policy's historical impact matches what
would happen in production. The reference implementation ports the operator and
conflict-resolution semantics from `backend/app/policy_engine` into PySpark.

## Free Edition constraints

Sized for Databricks Free Edition: moderate sample sizes (50k–500k historical
requests, 100k–2M approval/audit events), scheduled batch and on-demand jobs
only, no continuously-running streaming, and small sequential task graphs. The
project stays demonstrable even when no job is actively running, because the
`MockAnalyticsProvider` returns representative results locally.
