# Source File Catalog

Organizes the primary file responsibilities, inputs/outputs, change impact, and execution risk of `port_strategy_decision`.

This document is not a full repository inventory. It manages only the files needed to understand and maintain the Decision flow.

## 1. Document Purpose

| Item | Value |
|---|---|
| Target | `port_strategy_decision` root and `docs/source-file-catalog.md` |
| Basis | Currently documented file structure, imports, entrypoints, and data contracts |
| Excluded | build artifacts, cache, IDE files, `__pycache__`, one-time dumps |
| Primary perspective | File responsibility, input, output, DB impact, execution risk, change linkage |
| Actual execution | Not performed during the documentation reorganization |
| Unconfirmed items | Do not assume content that requires a final comparison against the actual code |

## 2. Service Flow

| Stage | Responsibility |
|---|---|
| Feature Load | Query the total market/stock feature and universe |
| Market Decision | Judge the market state and allowable exposure range |
| Buy Filter | Select buy candidates |
| Sizing | Compute the allocated quantity and weight per candidate |
| BUY Signal | Store the READY signal that the execution layer will consume |
| BLOCK Watch | Store only watch candidates without creating a BUY |
| Position Decision | Evaluate active positions as HOLD/SELL/SKIP |
| State Update | Store the position decision and the latest evaluated state |

## 3. Root and Common Files

| File | Role |
|---|---|
| `__init__.py` | The import reference point for the `port_strategy_decision` package |
| `db_config.py` | Manage the `INTEREST_DB_*` environment variables and the Decision DB connection settings |
| `decision_comparator.py` | Compare operational Decision results against Shadow JSON and generate a report |
| `decision_comparison_ecs_run.py` | Wrapper that runs the Comparison on ECS |
| `requirements.txt` | List of Python dependencies to install in the container |
| `Dockerfile` | Define the Daily Decision container image and the default CMD |
| `.dockerignore` | Exclusion rules for the image build context |
| `pytest.ini` | pytest configuration |
| `.github/workflows/` | GitHub Actions → CodeBuild trigger |
| `.devops/` | CI buildspec and smoke scripts |
| `tests/` | import/evaluator version contract tests |

### 3.1 `__init__.py`

| Item | Value |
|---|---|
| Responsibility | Package initialization |
| Functional logic | None |
| Change impact | The `python -m port_strategy_decision.<module>` import structure |
| Caution | Do not delete arbitrarily even though it appears to have no functionality |

### 3.2 `db_config.py`

| Item | Value |
|---|---|
| Responsibility | Centralize the PostgreSQL connection settings |
| Primary input | `INTEREST_DB_HOST`, `PORT`, `NAME`, `USER`, `PASSWORD` |
| Password | Injected externally with no default |
| Search path | Configure the search order of the Decision-related domain schemas |
| Call impact | A DB connection may occur when a connection is created |
| Change risk | The default DB, schema order, and credential-handling contract |
| Caution | Do not record actual connection values in documentation or logs |

### 3.3 `requirements.txt`

| Item | Value |
|---|---|
| Currently declared dependency | `psycopg2-binary` |
| Common handling | `port_strategy_common` is not a requirement; it is installed as a 1.0.0 Wheel during Docker build |
| Change impact | Image build and runtime import |
| Caution | Do not arbitrarily add/remove dependencies without confirming actual imports |

### 3.4 `Dockerfile`

| Item | Value |
|---|---|
| Base image | Python 3.13 slim |
| Included targets | `port_strategy_common`, `port_strategy_decision` |
| Common installation | `--no-deps` install of the 1.0.0 Wheel in `.devops/packages` |
| Default CMD | `python -m port_strategy_decision.daily_buy_signal_run` |
| Other entrypoints | A command override can be used at execution time |
| Operational position | ECS RunTask or the same container execution target |
| Repository boundary | ECR push and task definition registration are in the deployment domain |
| Caution | Do not record actual URI, ARN, subnet, and security group in documentation |

### 3.5 CI/Deployment Configuration

| File | Role |
|---|---|
| `.github/workflows/decision-codebuild.yml` | Owns CodeBuild, Candidate Shadow, CloudWatch collection, Comparator, GitHub Summary, `production` approval, and Production Promotion |
| `.devops/codebuild/buildspec.yml` | Quality gates, Common Wheel download, Docker build, optional ECR push |
| `.devops/scripts/container-smoke.py` | import-only smoke, no DB connection/run function call |
| `.devops/scripts/entrypoint-smoke.py` | entrypoint smoke that runs only the argparse `--help` path |
| `.dockerignore` | Exclusion rules for the image build context |

| Item | Value |
|---|---|
| Authentication | GitHub OIDC |
| Common Wheel | Prepare the CodeArtifact 1.0.0 Wheel in `.devops/packages` |
| Wheel tracking | `.devops/packages/*.whl` is a git-ignored build artifact |
| ECR push | Performed only when `PUSH_IMAGE=true` |
| Execution risk | buildspec includes AWS/Docker calls; do not run during documentation work |
| Sensitive information | Account ID, ARN, full Digest, and full CodeArtifact identifiers not recorded |

### 3.6 Tests

| File | Role |
|---|---|
| `pytest.ini` | pytest configuration |
| `tests/conftest.py` | Register the `port_strategy_decision` package for the flat layout |
| `tests/test_import_contract.py` | Decision/Common module import contract (no DB/run call) |
| `tests/test_position_version_contract.py` | Evaluator version default v1, supported {v1,v2} contract |

| Item | Value |
|---|---|
| Nature | Static contract validation with no side effects |
| Execution risk | No DB/order/AWS access |
| Linkage | buildspec Unit/Contract Test stage |

## 4. Daily Buy Signal

The Daily Buy flow reads features, performs market, filter, and sizing, and then stores a BUY signal or BLOCK watch.

| Order | File |
|---|---|
| 1 | `daily_buy_signal_run.py` |
| 2 | `daily_feature_loader.py` |
| 3 | `backtest_market.py` |
| 4 | `backtest_filter.py` |
| 5 | `backtest_sizing.py` |
| 6 | `daily_signal_builder.py` |
| 7 | `daily_repository.py` |
| Branch | `daily_block_watch_builder.py`, `daily_block_watch_repository.py` |

### 4.1 `daily_buy_signal_run.py`

| Item | Value |
|---|---|
| Responsibility | Orchestrate the full Daily BUY flow |
| Primary input | Run date, data date, total feature, and strategy config |
| Primary processing | Feature load, market, filter, sizing, and storage |
| Normal-market output | Daily run and BUY signal |
| BLOCK-market output | watch candidate without a BUY signal |
| Status handling | Update the Daily run lifecycle |
| DB impact | Query and write |
| Downstream impact | Can generate a signal for StrategyExecution to consume |
| Execution modes | Operational mode and read-only `--shadow` mode (write_count=0, JSON) |
| Shadow output | Include `target_qty` for Comparison in the Shadow BUY JSON |
| Execution risk | Operational mode changes actual operational data |
| Caution | Do not run during documentation/static analysis |

### 4.2 `daily_feature_loader.py`

| Item | Value |
|---|---|
| Responsibility | Query the Daily decision inputs |
| Date responsibility | Determine run date and data date |
| Market input | `pre_total_market_daily_feature` |
| Stock input | `pre_total_stock_daily_feature` |
| Universe input | `stock_universe` |
| DB impact | Query |
| Change risk | Date basis, table, filter, and row shape |
| Linked files | `daily_buy_signal_run.py`, `backtest_market.py`, `backtest_filter.py` |
| Caution | Do not arbitrarily convert a missing feature and empty result into a normal value |

### 4.3 `daily_signal_builder.py`

| Item | Value |
|---|---|
| Responsibility | Convert sizing results into a storable BUY signal row |
| Primary input | Sizing results and stock feature |
| Primary output | `strategy_daily_signal` storage format |
| Fixed meaning | `signal_type=BUY` |
| Initial status | `signal_status=READY` |
| Primary payload | Feature snapshot, buy info, raw feature, and entry reason |
| Direct DB write | None |
| Change risk | Field names, status values, reasons, and source table meaning |
| Caution | The Builder output is connected to the StrategyExecution contract |

### 4.4 `daily_repository.py`

| Item | Value |
|---|---|
| Responsibility | Daily run and BUY signal persistence |
| Primary tables | `strategy_daily_run`, `strategy_daily_signal` |
| Primary processing | Creation, query, status update, and signal upsert |
| DB impact | Read and write |
| Re-run risk | Same-reference-date duplication or existing-row update |
| Change risk | Unique key, run status, signal status, and upsert |
| Linked files | `daily_buy_signal_run.py`, `daily_signal_builder.py` |
| Caution | Confirm the transaction boundary so it is not marked successful after a partial store |

## 5. BLOCK Watch

BLOCK Watch is an auxiliary flow that, when the market is BLOCK, does not create a BUY signal and leaves only strong exception candidates for watching.

### 5.1 `daily_block_watch_builder.py`

| Item | Value |
|---|---|
| Responsibility | Convert BLOCK candidate evaluation results into storage rows |
| Common logic | `evaluate_block_watch_candidate` |
| Primary input | Stock feature and BLOCK-regime candidate information |
| Primary output | `strategy_block_watch_candidate` storage format |
| BUY generation | None |
| Order generation | None |
| Direct DB write | None |
| Change risk | Candidate criteria, reason, and payload contract |
| Caution | Do not turn it into a BUY-bypass path |

### 5.2 `daily_block_watch_repository.py`

| Item | Value |
|---|---|
| Responsibility | Store and clean up BLOCK watch candidates |
| Primary table | `strategy_block_watch_candidate` |
| Primary processing | Upsert and per-daily-run deletion |
| DB impact | Write and delete |
| Re-run risk | Scope of deleting existing candidates and regenerating |
| Change risk | Unique key, delete condition, and transaction |
| Linked files | `daily_buy_signal_run.py`, `daily_block_watch_builder.py` |
| Caution | Confirm the scope so candidates from another run or reference date are not deleted |

## 6. Market/Filter/Sizing Adapter

These files connect the decision logic of `port_strategy_common` to the row and object contracts of the Decision layer.

### 6.1 `backtest_market.py`

| Item | Value |
|---|---|
| Responsibility | Convert the Market feature into the Common market context |
| Common function | `common_decide_market` |
| Primary input | Total market feature row |
| Primary output | Decision-layer `MarketDecision` |
| Direct DB access | None |
| Change risk | Context field, config, and `MarketDecision` mapping |
| Reuse | Daily Buy and decision snapshot |
| Caution | Do not reinterpret the meaning of the Common function result in Decision |

### 6.2 `backtest_filter.py`

| Item | Value |
|---|---|
| Responsibility | Connect stock feature candidates to the Common buy filter |
| Common function | `common_filter_buy_candidates` |
| Primary input | Stock feature list and market decision |
| Primary output | Passed/excluded candidates and reasons |
| Direct DB access | None |
| Change risk | Candidate row field, filter config, and reason |
| Reuse | Daily Buy and decision snapshot |
| Caution | Do not confuse a filter rejection with missing data |

### 6.3 `backtest_sizing.py`

| Item | Value |
|---|---|
| Responsibility | Connect the position allocation calculation for filter-passed candidates |
| Common function | `common_allocate_positions` |
| Primary input | Buy candidate and market decision |
| Primary output | Sizing result per candidate |
| Direct DB access | None |
| Change risk | Quantity/weight meaning and `SIZING_CONFIG` |
| Reuse | Daily Buy and decision snapshot |
| Caution | Do not arbitrarily change the meaning of rounding, minimum order, and exposure |

## 7. Decision Snapshot Candidate

### 7.1 `backtest_decision_run.py`

| Item | Value |
|---|---|
| Responsibility | Output a single-day market/filter/sizing snapshot |
| Primary input | market/stock feature from the DB |
| Used adapters | `backtest_market.py`, `backtest_filter.py`, `backtest_sizing.py` |
| Run store | Does not use the Common run store |
| Run id generation | None |
| DB impact | Feature query |
| Output | Decision snapshot console output |
| Classification | An execution candidate of a backtest nature |
| Execution risk | Operational DB query and data output |
| Caution | Do not run under documentation work and backtest-prohibition scope |

## 8. Daily Position Decision

The Position flow combines the latest completed daily run, active positions, broker snapshot, and feature to store a HOLD, SELL, or SKIP decision.

| Order | File |
|---|---|
| 1 | `daily_position_signal_run.py` |
| 2 | `daily_position_repository.py` |
| 3 | `daily_position_evaluator.py` or `daily_position_evaluator_v2.py` |
| 4 | `daily_position_repository.py` |

### 8.1 `daily_position_signal_run.py`

| Item | Value |
|---|---|
| Responsibility | Orchestrate Position query, evaluation, storage, and summary |
| Primary input | Latest completed run, active position, broker snapshot, and feature |
| Evaluator | v1 or v2, operational default v1 |
| Execution modes | Operational mode and read-only `--shadow` mode (write_count=0, JSON) |
| Primary output | HOLD, SELL, SKIP decision |
| DB impact | Query and write |
| State impact | Update `strategy_position_state` latest evaluation |
| Downstream impact | Can be input to the StrategyExecution sell decision |
| Execution risk | Operational mode changes the position decision |
| Caution | Do not run during documentation/static analysis |

### 8.2 `daily_position_evaluator.py`

| Item | Value |
|---|---|
| Responsibility | Daily Position v1 decision |
| Primary criteria | Hard stop, minimum/maximum holding days, and market BLOCK |
| Additional criteria | Quality degradation and in-profit HOLD |
| Primary output | HOLD, SELL, or SKIP storage dict |
| Direct DB access | None |
| Direct DB write | None |
| Change risk | Criteria priority, status values, and reasons |
| Caution | Maintain compatibility with the existing operational SELL v1 meaning |

### 8.3 `daily_position_evaluator_v2.py`

| Item | Value |
|---|---|
| Responsibility | Combine daily validation and the Common sell decision |
| Preceding processing | Required validation for daily operations |
| Common function | `common_evaluate_backtest_sell` |
| Primary output | Map the Common result into the Daily decision format |
| Direct DB access | None |
| Change risk | Preceding validation order, mapping, status, and reason |
| Caution | Do not omit the Common result or convert it to a different meaning |

### 8.4 `daily_position_repository.py`

| Item | Value |
|---|---|
| Responsibility | Query needed for the Position decision and store results |
| Primary query | Active position, broker snapshot, stock/market feature |
| Primary storage | `strategy_daily_position_decision` |
| State update | `strategy_position_state` latest evaluation |
| DB impact | Read and write |
| Re-run risk | Duplication or update of the same position/reference-date decision |
| Change risk | Join basis, unique key, upsert, and latest update |
| Caution | Distinguish a missing broker snapshot from an actual 0 position |

## 9. Validation/Query Tools

### 9.1 `daily_validator.py`

| Item | Value |
|---|---|
| Responsibility | Query the latest daily run and linked signals |
| DB impact | Query |
| Output | Operational data console output |
| Validation nature | An auxiliary tool for a human to inspect storage results |
| Change risk | Query basis and output scope |
| Security risk | Possible exposure of account/stock/operational data |
| Execution condition | First confirm the output fields and target environment |
| Caution | Do not regard it as a safe static analysis tool |

### 9.2 `decision_comparator.py`

| Item | Value |
|---|---|
| Responsibility | Compare operational Decision results against Shadow JSON and generate a report |
| Input | Shadow JSONL and operational DB query results |
| Output | Comparison JSON report |
| Results | MATCH / DIFFERENCE / REVIEW_REQUIRED / INVALID |
| DB impact | Operational DB read-only query |
| Change risk | Promotion review meaning, BUY/Position identity, and comparison classification |
| Caution | Do not store the comparison result as a Decision decision result |

### 9.3 `decision_comparison_ecs_run.py`

| Item | Value |
|---|---|
| Responsibility | Wrapper for running the Comparison on ECS |
| Input | gzip+base64 Shadow JSONL environment variable |
| Processing | Restore payload → run comparator subprocess |
| Output | base64 report marker and Comparison result marker |
| DB impact | read-only query through the Comparator |
| Change risk | GitHub Workflow report parsing and Approval linkage |
| Caution | It is not the operational BUY/Position entrypoint |

## 10. Data Contracts

### 10.1 Primary Inputs

| Data | Role |
|---|---|
| `pre_total_market_daily_feature` | Market decision input |
| `pre_total_stock_daily_feature` | Buy filter, sizing, and position evaluation input |
| `stock_universe` | LEFT JOIN target for enriching the company name (company_name) |
| Active position | Held position evaluation target |
| `connector_balance_snapshot` | Confirm the latest broker snapshot reference date in position evaluation |
| `connector_position_snapshot` | Confirm broker holding quantity and state |

### 10.2 Primary Outputs

| Data | Role |
|---|---|
| `strategy_daily_run` | Daily Buy execution unit and lifecycle |
| `strategy_daily_signal` | READY BUY decision |
| `strategy_block_watch_candidate` | Watch candidates in a BLOCK regime |
| `strategy_daily_position_decision` | HOLD/SELL/SKIP decision history |
| `strategy_position_state` | Latest strategy evaluation state per position |

### 10.3 Contracts to Confirm on Change

| Item | Item to Confirm |
|---|---|
| Table | Schema, table name, and search path |
| Column | Type, NULL allowance, and meaning |
| Key | Unique key and group key |
| Date | Run date, data date, and reference date |
| Status | Run, signal, and position status values |
| Reason | Strings consumed by Common and downstream |
| Payload | Feature snapshot and JSON shape |
| Transaction | Partial success and rollback scope |
| Re-run | Duplication, delete, and upsert behavior |

## 11. Execution Risk Classification

| Level | Meaning |
|---|---|
| Read | Can query the DB and output operational data |
| Write | Can insert/update/upsert Strategy tables |
| Delete | Can delete rows for a specific run or reference date |
| Downstream impact | Can generate an artifact that the Execution layer will consume |

### 11.1 Per-File Risk

| File | Risk |
|---|---|
| `daily_buy_signal_run.py` | Query, write, and impact on the downstream BUY flow |
| `daily_repository.py` | Daily run/signal write |
| `daily_block_watch_repository.py` | Watch candidate write/delete |
| `daily_position_signal_run.py` | Query, decision storage, and state update |
| `daily_position_repository.py` | Position decision write and state update |
| `backtest_decision_run.py` | DB query and snapshot output |
| `daily_validator.py` | DB query and operational data output |
| `decision_comparator.py` | Operational DB read-only query and Comparison report generation |
| `decision_comparison_ecs_run.py` | Comparator wrapper, read-only query |
| `daily_feature_loader.py` | DB feature query |
| Builder/Evaluator/Adapter | No direct DB write, but affects the storage contract |

### 11.2 Targets Not Run During Documentation Work

| Target | Reason |
|---|---|
| Daily Buy entrypoint | Can change the Strategy run and BUY signal |
| Position entrypoint | Can change the Position decision and state |
| Repository functions | Can write/delete the DB |
| Backtest snapshot | An operational DB query occurs |
| Validator | Can output operational data |
| Container default CMD | Runs the Daily Buy entrypoint |
| AWS RunTask | Connects to actual operational execution |

## 12. `port_strategy_common` Linkage

| Area | Linkage |
|---|---|
| Config | Strategy name, engine version, and decision config |
| Market | `common_decide_market` |
| Buy Filter | `common_filter_buy_candidates` |
| Sizing | `common_allocate_positions` |
| Guard | Buy guard and size haircut family |
| BLOCK Watch | `evaluate_block_watch_candidate` |
| Sell | `common_evaluate_backtest_sell` |

### Change Cautions

| Item | Principle |
|---|---|
| Public functions | Do not change names/signatures without an explicit request |
| Dataclass | Preserve the field name and type contract |
| Enum/status values | Confirm downstream compatibility |
| Reason strings | Confirm the impact on stored data and the view/execution layer |
| Config | Confirm default and snapshot compatibility |
| Wheel installation | Keep the 1.0.0 Wheel installation method consistent with the Dockerfile/buildspec |

## 13. AWS and Operational Position

| Item | Value |
|---|---|
| Paper Daily Step 6 | `daily_buy_signal_run.py` |
| Paper Daily Step 7 | `daily_position_signal_run.py` |
| Orchestration | Scheduler and Step Functions responsibility |
| Execution method | ECS RunTask or the same container |
| Default image CMD | Daily Buy Signal |
| Position execution | Command override required |
| Repository evidence | Dockerfile, Python entrypoint, and `.devops`/`.github` CI configuration |
| External operational facts | Cluster, task definition, and Scheduler managed in documentation |

Do not confuse the structure confirmed from repository files with the actual current AWS state.

## 14. Documentation Files

| File | Role |
|---|---|
| `AGENTS.md` | Work scope, safety, data contracts, and completion criteria |
| `README.md` | Service structure, flow, configuration, and operational AS-IS |
| `CHANGELOG.md` | Functional/documentation-standard change history |
| `docs/source-file-catalog.md` | File responsibility, input/output, and change impact |

### Per-Document Update Criteria

| Document | Update Condition |
|---|---|
| `AGENTS.md` | Work rules, safety standards, and required contracts change |
| `README.md` | Service responsibility, flow, configuration, entrypoint, and operational position change |
| `CHANGELOG.md` | Actual features, structure, or documentation standards change |
| `docs/source-file-catalog.md` | File addition/deletion/move, responsibility, input/output, and execution risk change |

Do not create date-specific `docs/worklog/*.md` files anew. Preserve past creation facts only as historical entries at the time in the CHANGELOG.

## 15. Cleanup Candidates

| File | Current Judgment |
|---|---|
| `backtest_decision_run.py` | Kept as a snapshot tool that queries the DB |
| `daily_validator.py` | Kept as an operational query/output tool |
| Other tracked source | No files currently confirmed for deletion |

Do not delete a file before it meets the following conditions.

| Confirmation | Basis |
|---|---|
| Import | Not referenced by another file |
| Entrypoint | Not called from Local, Docker, and AWS commands |
| DB contract | Not used for operational validation or manual recovery |
| Document | Responsibility organized in the README, CHANGELOG, and catalog |
| Approval | The user's explicit deletion request |

## 16. Catalog Update Conditions

When the following changes occur, update this document in the same task.

| Change | Reflected Content |
|---|---|
| File addition | Add role, input, output, and risk |
| File deletion | Remove references and confirm the deletion history |
| File move | Fix the path and import/entrypoint impact |
| Entrypoint change | Reflect the Daily Step and Docker CMD |
| Table change | Fix the input/output contract and repository responsibility |
| Status change | Fix the Builder, repository, and downstream impact |
| Common change | Fix the Adapter mapping and public contract |
| Docker change | Fix the runtime, Common Wheel installation, and command |
| CI/deployment configuration change | Reflect the workflow, buildspec, and smoke script |
| Execution risk change | Reclassify read/write/delete/downstream impact |
| Document system change | Fix the role consistency of AGENTS, README, and CHANGELOG |

Record only confirmed current responsibilities in the catalog. Do not add nonexistent files, assumed AWS resources, or unconfirmed behavior.
