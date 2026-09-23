# CHANGELOG

Records the change history of the features, data contracts, execution structure, and documentation standards of `port_strategy_decision`.

- Place the latest change at the top.
- Distinguish functional changes from documentation restructuring.
- Do not record sensitive information or one-time operational values.
- Do not create date-specific worklogs; leave primary changes in this document.

## 2026-08-10

### Repository/Branch

| Item | Value |
|---|---|
| Default branch | `master` → `main` transition |
| OIDC Trust | Cleaned up based on the main branch |
| Final work short SHA | `a01d90592a7c` |

### Decision Comparison Automation

| Item | Value |
|---|---|
| Added file | `decision_comparator.py` |
| Responsibility | Compare operational DB results against the Shadow CloudWatch JSON and generate the report JSON |
| Comparison targets | BUY and Position |
| DB impact | Operational DB read-only query, no new Decision result storage |
| Four result types | MATCH, DIFFERENCE, REVIEW_REQUIRED, INVALID |
| INVALID handling | Failure path, blocks Promotion |

### Candidate Shadow and Comparator Runner

| Item | Value |
|---|---|
| Added file | `decision_comparison_ecs_run.py` |
| Responsibility | Restore the gzip+base64 Shadow JSONL, run the comparator, and output the base64 report marker |
| Candidate execution | Register the Candidate Image Revision in the Shadow Family separated from operations |
| Execution method | Run BUY Shadow → Position Shadow directly via GitHub Workflow ECS RunTask |
| Shadow contract | read-only, write_count=0, no order path linkage |
| BUY Shadow enrichment | Include the comparison `target_qty` in the Shadow BUY JSON |

### GitHub Approval and Production Promotion

| Item | Value |
|---|---|
| Workflow | Candidate Shadow → Comparison → Job Summary → production approval → Promotion linkage |
| Approval gate | GitHub `production` Environment manual approval |
| Reject | Confirmed Promotion not executed |
| Approve | Confirmed Production Promotion executed |
| Promotion Image | Uses the approved identical Candidate Image without rebuild |
| BUY operational Command | `daily_buy_signal_run` retained |
| Position operational Command | Default v1 `daily_position_signal_run` retained |
| Revision transition | Register/transition a new Revision from the existing operational `:3` baseline |
| Target State Machines | Update/validate references of the related 5 operational State Machines |

### Validation

| Item | Value |
|---|---|
| Real-data Comparison | Succeeded with real data on 2026-08-10 |
| Market | BLOCK for both operations and Shadow, MATCH |
| BUY Shadow Signal | 0 records |
| Shadow Position Decision | 3 records, write_count=0 |
| Final result | `REVIEW_REQUIRED` |
| Review classification | 7 Position comparisons classified as requiring human review |
| Difference example | operational HOLD → Shadow SELL, Position removed from the Shadow evaluation set |
| Interpretation | Detected the operational v1 vs Shadow v2 and active position population difference, not a decision error |
| Full Workflow | Succeeded through Comparison → approval → Production Promotion |

### Work Scope

| Item | Value |
|---|---|
| Strategy decision logic change | None; operational Position default v1 retained |
| New feature | Comparison automation and Comparator ECS Runner |
| Shadow enrichment | Added `target_qty` to the BUY Shadow JSON |
| Operational DB impact | None; Comparison is read-only |
| Order execution | None |
| This documentation work | Update `AGENTS.md`, `README.md`, `CHANGELOG.md`, `docs/source-file-catalog.md` |
| Sensitive information | No verbatim recording of full ARN/Digest/Account ID/subnet/security group/local paths |

## 2026-07-31

### Decision DevOps Baseline

| Item | Value |
|---|---|
| GitHub Repository | `wooktae/port-strategy-decision` |
| Default branch | `master` |
| Source consistency | Confirmed Local/Remote/CodeBuild Source SHA match |
| Source short SHA | `ff4d285b87b9` |
| ECR Image Tag | `ff4d285b87b9` |
| Image short Digest | `3be7251875f9` |
| Common dependency | `port_strategy_common` 1.0.0 Wheel installed |

| CI Quality Gate | Content |
|---|---|
| Python Compile | `compileall` |
| Unit/Contract Test | import contract, position evaluator version contract |
| Static Analysis | Ruff |
| Host Smoke | Import/Entrypoint smoke |
| Container Smoke | Import/Entrypoint smoke |
| Docker Build | image build |
| ECR Push | push only on a `PUSH_IMAGE=true` run |

| Item | Value |
|---|---|
| GitHub Actions | `workflow_dispatch` trigger |
| Authentication | GitHub OIDC-based CodeBuild execution |
| Source delivery | Pass the GitHub Commit SHA as the CodeBuild Source Version |

### Shadow Canary

| Item | Value |
|---|---|
| Family separation | BUY/Position each in a Shadow Family separated from operations |
| Shadow Revision | `:1` each |
| BUY Shadow | `--shadow` added to the operational entrypoint |
| Position Shadow | `--shadow --evaluator-version v2` |
| Storage contract | read-only, write_count=0 |
| Result | CloudWatch structured JSON |
| State Machine | Sequential BUY → Position execution on a Shadow-dedicated State Machine |
| Execution result | State Machine SUCCEEDED, both Container Exit Code 0 |
| Order linkage | Not linked to the operational Step Functions/StrategyExecution/orders |

| Item | Value |
|---|---|
| Initial failure | Step Functions Role missing `ecs:RunTask` permission for the Shadow Family |
| Remediation | Added only the minimal Shadow Family permission while preserving operational permissions |
| Re-run | Succeeded after the permission remediation |
| Managed Policy | Default version v3 → v4 |
| Real-data limit | With input BLOCK and 0 positions, the v1/v2 actual-difference comparison was limited; further comparison needed |

The first Shadow result confirmed Run Date/Data Date consistency, Market Signal BLOCK, 0 BUY Candidate/Signal/Block Watch, 0 active Position/HOLD/SELL/SKIP, and, based on the Position Shadow Evaluator v2, both BUY/Position write_count of 0.

### Operational Promotion and Rollback

| Item | Value |
|---|---|
| Operational BUY Revision | `:2` → `:3` registration |
| Operational Position Revision | `:2` → `:3` registration |
| Operational Command | No Shadow option |
| New Image | Tag `ff4d285b87b9`, short Digest `3be7251875f9` |
| Target State Machines | 5 referencing the Decision Revision |
| Promotion | `:2` → `:3` transition and active reference confirmation |
| Rollback | `:3` → `:2` recovery and previous Revision reference confirmation |
| Re-promotion | `:2` → `:3` re-transition and final Revision `:3` reference confirmation |
| Shadow retention | Shadow Revision `:1` retained |

The 5 target State Machines are `portfolio-paper-daily-step1-11-safe`, `portfolio-paper-daily-step1-17-approval`, `portfolio-paper-daily-step6-only`, `portfolio-paper-daily-step6-step7-step8-step9-step10-step11`, and `portfolio-paper-daily-step7-only`. The promotion/Rollback/re-promotion used the same Image Digest without rebuild.

### Operational E2E

| Item | Value |
|---|---|
| BUY execution | `portfolio-paper-daily-step6-only` SUCCEEDED |
| Position execution | `portfolio-paper-daily-step7-only` SUCCEEDED |
| Executed Revision | Operational BUY/Position Revision `:3` |
| Container | Both executions Exit Code 0 |
| Image | Expected Tag/Digest match |
| Log | CloudWatch confirmed, 0 error patterns |
| Daily Run | Run ID 86 used |
| BUY result | Market Signal BLOCK, 0 Candidate/Signal |
| Position result | Operational Evaluator v1, 0 Position/Decision |
| Execution scope | Only Step 6/7 executed; Step 8–17, StrategyExecution, and orders not executed |

This E2E is validation up to the Decision stage. It did not validate the full Paper Daily Step 1–17 or order fills. The 0-record result is a normal result given the input conditions, not a validation failure.

### Follow-up Tasks

| Item | Value |
|---|---|
| Automatic comparison | Automatic Comparison Task for operational DB results vs Shadow JSON (unimplemented) |
| BUY comparison | Real-data comparison on a day when BUY stocks/quantities occur |
| Position comparison | v1/v2 real-data comparison on a day when HOLD/SELL/SKIP occur |
| Review | Decision dev team review of decision-reason differences and refinement of promotion criteria |

The Comparison Task is not complete but a follow-up task.

### Work Scope

| Item | Value |
|---|---|
| Strategy decision logic change | None |
| Shadow execution feature | entrypoint `--shadow` read-only mode |
| CI/Container deployment configuration | Added workflow, buildspec, smoke script, contract test |
| AWS change | Task Definition Revision, Shadow/operational State Machine, IAM least privilege |
| Operational DB impact | None (Shadow read-only, operational E2E result 0 records) |
| Order execution | None |
| This documentation work | Update `AGENTS.md`, `README.md`, `CHANGELOG.md` |
| Sensitive information | No verbatim recording of full ARN/Digest/Account ID/local paths |

## 2026-07-22

### Decision Documentation Standard Reorganization

| Item | Value |
|---|---|
| Change scope | Consistency reorganization of `AGENTS.md`, `README.md`, `CHANGELOG.md`, `docs/source-file-catalog.md` |
| Functional change | None |
| Code/config change | None |
| DB/AWS execution | None |
| Operational data change | None |

### AGENTS.md

| Item | Change Content |
|---|---|
| Highest-priority rules | Placed readability, 2-column tables, long-cell splitting, and duplication-prevention standards at the front of the document |
| Work scope | Clarified the principle of internal `port_strategy_decision` work and read-only for other MS |
| Responsibility boundary | Separated the responsibilities of Decision from Crawler, Preprocessor, StrategyExecution, MarketConnector, View, and Research |
| Daily Buy | Distinguished the feature loading, market, filter, sizing, BUY signal, and BLOCK watch flow |
| Position | Distinguished the v1/v2 evaluator and HOLD/SELL/SKIP decision responsibilities |
| Data contract | Organized the total feature input and daily run, signal, watch, position decision output contracts |
| Common contract | Specified the restriction on changing public functions, dataclasses, enums, status values, and reason strings |
| DB safety | Added standards for confirming unique key, upsert, delete scope, transaction, and re-run impact |
| Status safety | Added principles to prevent partial success, post-exception success handling, and duplicate storage |
| Execution restriction | Detailed the prohibition scope for daily signal, backtest, DB write, AWS, orders, and external calls |
| Document linkage | Specified that `docs/source-file-catalog.md` be updated together when file responsibilities change |
| Worklog | Changed the current document operation standard to prohibit new date-specific worklog creation |

### README.md

| Item | Change Content |
|---|---|
| Document purpose | Restructured to focus on the current structure and operational AS-IS rather than work rules |
| Service summary | Placed the layer, primary inputs, outputs, entrypoints, and external dependencies in the first summary table |
| Daily Buy flow | Organized the flow from total feature to market, filter, sizing, and BUY or BLOCK watch |
| Position flow | Organized the HOLD/SELL/SKIP flow combining daily run, active position, broker snapshot, and feature |
| BUY/SELL meaning | Clarified that the Decision artifact differs from the actual order submission responsibility |
| Input contract | Separated the roles of market feature, stock feature, universe, and broker snapshot |
| Output contract | Distinguished daily run, signal, block watch, position decision, and position state |
| File structure | Restructured nested long-form lists into role-based 2-column tables |
| Common dependency | Organized the market, filter, sizing, guard, and sell reuse points |
| AWS position | Distinguished the execution position at Paper Daily Step 6 and Step 7 |
| Container | Organized the default CMD, command override, Common vendoring, and deployment responsibility |
| DB configuration | Organized `INTEREST_DB_*`, the default DB, and the search path description in table form |
| Status cautions | Reinforced cautions on partial success, re-run, missing feature, transaction, and freshness |
| Document system | Distinguished the roles of AGENTS, README, CHANGELOG, and source catalog |

### docs/source-file-catalog.md

| Item | Change Content |
|---|---|
| Composition basis | Kept the per-file long-form list centered on flow, input/output, DB impact, and execution risk |
| Update conditions | Specified the catalog linkage standard when files, entrypoints, tables, Common, and Docker change |
| Worklog | Kept no date-specific worklog creation; kept only the source catalog under `docs` |

### Reflected Actual Code Comparison

| Item | Change Content |
|---|---|
| `stock_universe` | Corrected the Daily input role to a LEFT JOIN target for enriching company_name |
| `connector_balance_snapshot` | Corrected from being a Daily Buy available-cash input to confirming the latest broker snapshot reference date in Position evaluation |
| Daily Buy processing | Excluded the uncalled guard stage from the `daily_buy_signal_run` execution flow description |

### Documentation Operation Decisions

| Item | Value |
|---|---|
| New worklog | Not created |
| Past worklog records | Preserved in the CHANGELOG as change facts at the time |
| Detailed file responsibility | Managed in `docs/source-file-catalog.md` |
| Actual code comparison | Completed the four-document consistency check via static confirmation of entrypoint, loader, repository, and evaluator |
| Sensitive information | Verbatim recording prohibited |
| One-time operational values | Excluded from CHANGELOG recording |

## 2026-07-01

### Documentation of AWS Operational Position and Responsibility Boundary

| Item | Change Content |
|---|---|
| README | Added the Decision responsibility boundary, AWS operational position, and container image description |
| Execution form | Corrected the execution examples to the `python -m port_strategy_decision.<module>` form |
| Step 6 | Organized the Daily Buy Signal entrypoint based on `daily_buy_signal_run.py` |
| Step 7 | Organized the Position Signal entrypoint based on `daily_position_signal_run.py` and the v1/v2 evaluator |
| Service boundary | Separated responsibilities from Preprocessor, StrategyExecution, MarketConnector, View, Research, and Scheduler |
| Source catalog | Added `Dockerfile`, `requirements.txt`, and per-file execution risk |
| Worklog | Created `docs/worklog/2026-07-01.md` per the document operation standard at the time |

### Work Scope

| Item | Value |
|---|---|
| Functional change | None |
| Code/config change | None |
| Actual execution | No daily signal, backtest, execution order, DB DDL/DML, external API, crawling, or order execution |
| External MS records | Detailed operational logs outside this repository's scope not reflected |
| Sensitive information | No verbatim recording of AWS identifiers, DB connection values, accounts, and order numbers |

## 2026-05-28

### File Catalog and Code Description Reorganization

| Item | Change Content |
|---|---|
| Source catalog | Added `docs/source-file-catalog.md` organizing all file roles and execution cautions |
| Python description | Added module-level Korean docstrings and descriptions of core pipeline/DB functions |
| Backtest snapshot | Removed the Common run store dependency and run-creation call from `backtest_decision_run.py` |
| Execution meaning | Organized it as an entrypoint that outputs a single-day market, filter, and sizing snapshot |
| Document consistency | Reflected in the README and source catalog that it is a DB feature-query-based snapshot |
| Local path | Replaced the local absolute path comment at the top of the file with a module-role docstring |
| Worklog | Created `docs/worklog/2026-05-28.md` per the document operation standard at the time |

### Work Scope

| Item | Value |
|---|---|
| Decision functional change | Removed the Common run-record dependency in `backtest_decision_run.py` |
| Actual DB/operational execution | None |
| Sensitive information | Not recorded in documentation or comments |

## 2026-05-27

### DB Configuration and Schema Structure Reorganization

| Item | Change Content |
|---|---|
| DB configuration | Externalized connection settings via `get_db_config()` in the local `db_config.py` |
| Environment variables | Organized into `INTEREST_DB_*`-based settings |
| Password | Removed the hardcoded candidate and applied required `INTEREST_DB_PASSWORD` validation |
| Default DB | Changed the local default DB name from `interest_crawler` to `portfolio` |
| Schema structure | Documented the single DB `portfolio` and per-domain schema structure |
| Search path | Documented the schema search order of the Decision modules |
| SQL compatibility | Retained the structure where existing SQL operates based on the search path |

### Work Scope

| Item | Value |
|---|---|
| Actual DB execution | None |
| Daily/Backtest execution | None |
| External call/order | None |
| Sensitive information | No verbatim recording |

## 2026-05-26

### Initial Documentation and Local Candidate Cleanup

| Item | Change Content |
|---|---|
| Initial documentation | Added `AGENTS.md`, `README.md`, and a worklog draft at the time |
| Cache cleanup | Cleaned up Python `__pycache__/` artifacts |
| Test candidates | Cleaned up 9 ignored local test/debug candidates |
| Preserved files | `backtest_decision_run.py` and `daily_validator.py` were not deleted and kept as held candidates |

### Cleaned-up Local test/debug Candidates

| File | Handling |
|---|---|
| `test_compare_common_buy_filter.py` | Cleaned up |
| `test_compare_common_buy_sizing.py` | Cleaned up |
| `test_compare_common_buy_toxic_guard.py` | Cleaned up |
| `test_compare_common_market.py` | Cleaned up |
| `test_compare_common_sell_logic.py` | Cleaned up |
| `test_compare_daily_position_v1_v2.py` | Cleaned up |
| `test_daily_buy_toxic_haircut.py` | Cleaned up |
| `test_daily_position_v1_v2_synthetic.py` | Cleaned up |
| `test_debug_daily_buy_toxic.py` | Cleaned up |

### Work Scope

| Item | Value |
|---|---|
| Authoring basis | Local file structure and import/entrypoint confirmation results at the time |
| Actual execution | No daily signal, backtest, execution order, DB, external API, crawling, or order execution |
| Sensitive information | No verbatim recording |
