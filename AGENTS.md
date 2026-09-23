# AGENTS.md - port_strategy_decision

## 0. Highest-Priority Documentation Readability Rules

All work prioritizes readable results together with accuracy.

| Item | Rule |
|---|---|
| Default table | New standalone summary tables use two columns by default. |
| Recommended columns | Prefer `Item / Value`, `File / Role`, `Layer / Responsibility`, `Status / Meaning`. |
| Existing table | When adding a row to an existing table, preserve its existing column structure. |
| Long cell | Put only 1–2 key facts in a cell; if there are 3 or more, split into multiple rows or a detailed document. |
| Length limit | Do not exceed 300 characters per table cell or 500 characters per Markdown line. |
| No repetition | Do not repeat the same explanation at length across the README, CHANGELOG, and source catalog. |
| Status expression | Clearly distinguish current implementation, design principles, operational facts, and unverified assumptions. |
| Verbatim output | Do not place raw logs, complete SQL, complete DB results, or verbatim sensitive information in documentation. |
| Encoding | Save Korean Markdown as UTF-8 without BOM. |

Document roles are separated as follows.

| Document | Role |
|---|---|
| `AGENTS.md` | The scope, safety, data contracts, and validation rules Kiro must follow when working |
| `README.md` | Current structure, responsibility boundaries, execution/configuration methods, and AS-IS operational understanding |
| `CHANGELOG.md` | Actual change history and preservation of facts at the time |
| `docs/source-file-catalog.md` | Role, input/output, and change impact of operationally and maintenance-important files |

## 1. Scope and Priority

- This file is the highest-priority working rule dedicated to `port_strategy_decision`.
- When working in this repository, do not use another microservice's `AGENTS.md` as the working basis.
- If there is a conflict with `.kiro/AGENTS.md`, this file's Decision-specific rules take precedence.
- Directly modify only the `port_strategy_decision` root and its subordinate files.
- Files outside the root are allowed only as read-only reference for contract confirmation.
- If the user specifies a target file, modify only that file.
- A full workspace scan, sub-agent, orchestrator, and new scanner creation are prohibited.
- Keep changes small and verifiable in scope.

## 2. Service Responsibility

This repository is the layer that reads the total feature produced by the Preprocessor and generates daily decisions.

| Layer | Decision Responsibility |
|---|---|
| Market | Judge the market state, exposure limits, maximum position count, and minimum score/flow criteria |
| Buy Filter | Filter stock features against buy candidate criteria |
| Sizing | Compute quantity and weight per candidate |
| Daily Buy | Create `strategy_daily_run`, `strategy_daily_signal` and update status |
| BLOCK Watch | Separately record only watch candidates during a BUY-blocked regime |
| Position | Evaluate active positions as HOLD, SELL, or SKIP |
| Adapter | Convert `port_strategy_common` decision results into the daily storage format |

The scope Decision does not own directly is as follows.

| Area | Owning Layer |
|---|---|
| External data collection | Crawler |
| raw data preprocessing and total feature generation | Preprocessor |
| execution plan and order request composition | StrategyExecution |
| broker order, fill, balance, and holding synchronization | MarketConnector |
| backtest scenarios and research reports | StrategyResearch |
| view query and approval UI | View |
| full batch orchestration | Scheduler and Step Functions |
| image build, ECR push, task definition registration | Deployment pipeline |

## 3. Core Execution Flow

### 3.1 Daily Buy Signal

| File | Role |
|---|---|
| `daily_buy_signal_run.py` | Entrypoint that reads the total feature and runs the market, filter, sizing, BUY, and BLOCK watch flow |
| `daily_feature_loader.py` | Query run date, data date, and market/stock feature |
| `backtest_market.py` | common market decision adapter |
| `backtest_filter.py` | common buy filter adapter |
| `backtest_sizing.py` | common sizing adapter |
| `daily_signal_builder.py` | Convert sizing results into the daily signal storage format |
| `daily_repository.py` | Query/store daily run and signal and update status |
| `daily_block_watch_builder.py` | Select watch candidates during a BLOCK regime |
| `daily_block_watch_repository.py` | Store block watch candidates and clean up the existing scope |

### 3.2 Daily Position Signal

| File | Role |
|---|---|
| `daily_position_signal_run.py` | Entrypoint that reads the latest completed run and active positions and generates HOLD, SELL, SKIP |
| `daily_position_evaluator.py` | daily position v1 decision |
| `daily_position_evaluator_v2.py` | v2 adapter that reuses the common sell decision after daily validation |
| `daily_position_repository.py` | Query position, broker snapshot, feature and store decisions |

### 3.3 Query and Auxiliary Entrypoints

| File | Handling Principle |
|---|---|
| `backtest_decision_run.py` | A single-day decision snapshot candidate; because it queries the DB, do not run it during documentation work. |
| `daily_validator.py` | May include DB queries and output, so decide whether to run it only after confirming its structure. |
| `decision_comparator.py` | An operational DB read-only query and Shadow JSON comparison tool; treat it as an operationally important file and do not run it during documentation work. |
| `decision_comparison_ecs_run.py` | An ECS Comparator wrapper; it is not the operational BUY/Position entrypoint. |
| test/debug/output files | Do not assume they are operational sources; before confirming evidence, describe them as candidates or local artifacts. |

## 4. Input Data Contract

Decision does not create source data directly. It reads the following inputs to make decisions.

| Input | Role |
|---|---|
| `pre_total_market_daily_feature` | market signal and market-level limit decision |
| `pre_total_stock_daily_feature` | Stock filter, sizing, and position evaluation |
| `stock_universe` | LEFT JOIN target for enriching the company name (company_name) |
| `connector_balance_snapshot` | Confirm the latest broker snapshot reference date in position evaluation |
| `connector_position_snapshot` | Confirm broker holding state |
| `strategy_position_state` | Latest evaluated state of the strategy position |

Input-related rules:

- Do not conflate run date and data date.
- Confirm the reference-date consistency of the market and stock feature within the same execution.
- Do not use a future reference date or unconfirmed data merely because it is the latest row.
- Distinguish a missing feature from an actual 0 value.
- Do not arbitrarily treat `NULL`, `0`, negatives, and string states as having the same meaning.
- Do not assume input column names and table structures.
- Before a contract change, confirm the impact on the loader, evaluator, repository, and downstream together.

## 5. Output and Status Contract

| Output | Meaning |
|---|---|
| `strategy_daily_run` | daily buy decision execution unit and final status |
| `strategy_daily_signal` | BUY candidates and sizing results |
| `strategy_block_watch_candidate` | Watch candidates in a BLOCK market |
| `strategy_daily_position_decision` | Position HOLD, SELL, SKIP decisions |
| `strategy_position_state` | Latest evaluated state of a position |

Do not change the following contracts without an explicit request.

- table and column names
- unique key and conflict key
- insert, update, delete, and upsert scope
- run status and decision status strings
- the meaning of market signal, BUY, BLOCK, HOLD, SELL, SKIP
- reason code and reason strings
- evaluator version and engine version
- fields and sort order that downstream reads

Status handling principles:

- Confirm the transition conditions for the start, complete, and failure states.
- Do not create a partial success where only the run is marked successful after some signals are stored.
- Do not overwrite with a success status after catching an exception.
- On re-run, confirm duplicate or residual rows for the same run date and data date.
- For a delete-then-insert structure, first confirm the delete scope and transaction boundary.
- When changing the repository call order, inspect the possibility of a partial commit.

## 6. Market, Filter, and Sizing Rules

- The market decision adapts the `port_strategy_common` result into the Decision format.
- Preserve the meaning of market signal, base exposure, max positions, min score, and flow criteria.
- When the market is BLOCK, do not generate a normal BUY signal.
- Block watch is not a BUY-bypass path but a separate watch artifact.
- Do not arbitrarily reinterpret the buy filter's score, quality, flow, and toxic guard criteria.
- Sizing preserves the meaning of available cash, exposure, max positions, minimum order unit, and haircut.
- Before silently converting a float-conversion failure or a missing value to 0, confirm the existing contract.
- Changing candidate order and tie handling can change the actual order candidates, so treat it as a functional change.

## 7. Position Decision Rules

- Do not treat the v1 and v2 evaluators as the same implementation.
- Distinguish the hard stop, minimum/maximum holding days, market BLOCK, quality degradation, and in-profit HOLD conditions.
- Preserve the structure where v2 first performs daily operational validation and then maps the common sell result.
- Distinguish a missing broker snapshot from an actual non-holding.
- Confirm the ticker/quantity consistency among the active position, position state, and broker position.
- Do not express SELL decision generation and actual order execution as the same responsibility.
- When updating position state latest, do not overwrite past decision history.
- Changes to evaluator version, reason, and priority can affect StrategyExecution or operational validation.

## 8. `port_strategy_common` Dependency

This repository reuses core decision logic from the common module.

| Area | Primary Common Contract |
|---|---|
| Config | strategy name, engine version, market/filter/sizing settings and snapshot |
| Market | common market context and market decision |
| Filter | common buy candidate filter |
| Sizing | common position allocation |
| Guard | buy guard and size haircut |
| BLOCK Watch | block watch candidate evaluation |
| Sell | common backtest sell decision |

The following items are connected to other services, so do not change them without an explicit request.

- public function names and import paths
- dataclass fields and default values
- enums and status strings
- reason code and reason text
- config keys and snapshot format
- the mapping that converts common results into the daily format

If a change to the common module is needed, do not resolve it by modifying only this repository. Separate the responsibilities of the caller and the common module and report them.

## 9. Database Rules

- Confirm the DB configuration based on the actual implementation of `db_config.py`.
- Do not assume environment variable names, defaults, or required values.
- Do not create a new default for the password.
- Use environment variables or a local secret loader for sensitive information.
- Changing the `search_path` order affects unqualified SQL resolution, so treat it as a contract change.
- When mixing schema-qualified SQL and search-path-based SQL, confirm the target schema.
- Do not assume columns, unique keys, and conflict targets without a basis in code and DDL.
- Before an SQL write change, confirm the insert, update, delete, upsert, and transaction scope.
- Confirm the commit and rollback locations and report the possibility of a partial store.
- When only a static check without an actual DB connection was performed, do not express it as completed AS-IS validation.

## 10. Execution and Operational Safety

Unless the user explicitly specifies otherwise, the following work is prohibited.

| Prohibited Work | Reason |
|---|---|
| Running `daily_buy_signal_run.py` | signal and run data may be created/updated |
| Running `daily_position_signal_run.py` | position decision and state may be updated |
| Running `backtest_decision_run.py` | a DB feature query occurs |
| Running `daily_validator.py` | DB queries and possible sensitive information output |
| Running backtest or research | affects research data and DB access |
| DB DDL/DML | risk of operational contract and data change |
| execution order generation | affects the StrategyExecution downstream flow |
| broker order/cancel | actual order impact |
| Running Crawler and Preprocessor | risk of upstream data change |
| External API call | network and external system impact |
| AWS CLI/SDK execution | ECS, Step Functions, and operational resource impact |
| Scheduler change | affects the automatic execution time and operational flow |
| Slack send | risk of misdelivered operational notifications |

For documentation work, do not even perform a Python module import before confirming the possibility of automatic execution or a DB connection.

### 10.1 Execution Mode Safety Rules

Clearly distinguish operational mode from `--shadow` mode.

| Item | Criterion |
|---|---|
| Shadow Transaction | Maintain the read-only, write count 0 contract |
| Shadow result | Output as CloudWatch structured JSON |
| Shadow linkage | Do not connect to the StrategyExecution/order path |
| Family separation | Separate the operational Task Definition from the Shadow Family |
| Operational Command | Do not mix in `--shadow` |
| Position default | The operational default is v1; do not confuse it with Shadow v2 validation |

## 11. Code Modification Rules

- Do not modify Python, Dockerfile, requirements, and configuration files without an explicit user request.
- Preserve existing function signatures, CLI options, and module entrypoints.
- Do not break the `python -m port_strategy_decision.xxx` execution structure.
- Avoid large-scale string replacement of the original Python files; make localized changes.
- Do not revert user changes.
- Do not delete legacy files based on assumption.
- Even if a file appears unused, first confirm evidence of import, Docker CMD, wrapper, and external calls.
- Do not create a flow that unconditionally outputs SUCCESS after a failure.
- Even after a code change, do not perform validation that requires operational execution; leave it as a limitation.

## 12. Testing and Validation

If tests exist, prioritize static/unit validation that isolates the DB and operational systems.

| Area | Priority Validation |
|---|---|
| Loader | run date, data date, missing feature, and reference-date consistency |
| Market | market signal and limit-value mapping |
| Filter | boundary score, missing values, and candidate order |
| Sizing | available cash, exposure, max positions, and rounding |
| BLOCK Watch | no BUY generation, watch candidate storage scope |
| Position v1 | stop, hold day, BLOCK, and quality conditions |
| Position v2 | preceding validation and common sell mapping |
| Repository | unique key, upsert, delete scope, and rollback |
| Re-run | same-reference-date duplication and idempotency |

Validation principles:

- For tests that require the DB, replace the connection and cursor with a mock or fixture.
- Do not use an actual broker snapshot, orders, or the operational DB.
- First confirm whether the test performs a DB or external call on import.
- Do not record a test that could not be run as passed.
- When only documentation is modified, validate only the document format and change scope.

## 13. AWS and Container Rules

- Confirm the `Dockerfile` base image, package path, Common Wheel installation, and CMD based on the actual file.
- Do not confuse the default CMD with the Step Functions command override.
- The Dockerfile in the repository is an execution image definition, not evidence of a completed deployment.
- Treat ECS RunTask, task definition, ECR image, and Step Functions state as external operational facts.
- Do not record the actual cluster, task definition ARN, image URI, subnet, security group, IAM role, and secret ARN verbatim in documentation.
- Record that `port_strategy_common` is not vendored but installed as a 1.0.0 Wheel, and that `.devops/packages/*.whl` is a git-ignored build artifact.

### 13.1 DevOps Validation Rules

| Item | Criterion |
|---|---|
| Source/Image consistency | Confirm the consistency of Source SHA, Image Tag, and Digest |
| PUSH_IMAGE | Distinguish `false` as the quality gate and `true` as the ECR Push purpose |
| Shadow execution | Distinguish Shadow Standalone execution from Shadow State Machine execution |
| Operational promotion | Distinguish Revision registration from active reference transition |
| Promotion validation | On promotion/Rollback/re-promotion, confirm all references of the related State Machines |
| E2E success | Confirm State Machine success, ECS Exit Code 0, expected Revision/Image execution, and logs |
| Container judgment | Do not judge failure by the `EssentialContainerExited` string alone; confirm the Exit Code |
| Scope confirmation | In the operational E2E, confirm that Step 8 onward and the order path are not called |
| Result distinction | Distinguish a 0-record result from a validation failure |
| Real-data limit | When real data does not occur, do not record logic-equivalence validation as complete |

### 13.2 Decision Comparison Rules

| Item | Criterion |
|---|---|
| Comparator results | Do not arbitrarily change the meaning of `MATCH`, `DIFFERENCE`, `REVIEW_REQUIRED`, `INVALID` |
| No result confusion | Do not treat `INVALID` and `REVIEW_REQUIRED` as having the same meaning |
| INVALID | Do not treat it as a normal Comparison and exclude it from Promotion candidacy |
| Evaluator boundary | Maintain the distinction between operational v1 and Shadow v2 |
| Candidate Shadow | Maintain the read-only, write_count=0 contract |
| Promotion Command | Do not mix `--shadow` or Shadow v2 into the operational Command |
| DB impact | When modifying the Comparator, do not add operational DB writes, and do not store the comparison result as a Decision result |
| Workflow change | When changing Comparison/Approval/Promotion, confirm the Candidate Artifact identity and the impact on the 5 operational State Machines |
| Document linkage | When adding a Comparison file or changing its responsibility, update `docs/source-file-catalog.md` together |

## 14. Security and Sensitive Information

- Do not output or document passwords, tokens, API keys, account numbers, webhook URLs, and actual DB connection information.
- For discovered sensitive information, do not quote the value itself; report only its existence and location.
- For example values, use `[REDACTED]` or an obvious placeholder.
- Do not leave the full value of broker order number, command id, and execution ARN in documentation.
- If logs or dumps contain account, per-stock holding quantities, and order information, summarize only the minimum necessary facts.
- Do not record full ARN, IAM Role ARN, Policy ARN, Task ARN, and Execution ARN.
- Do not record the AWS Account ID, subnet, security group, and full Image Digest.
- Do not record local temporary paths such as State Machine Definition backups.
- For DevOps facts, use only the following safe level.

| Allowed Item | Example |
|---|---|
| Task Definition | Family and Revision |
| State Machine | Name |
| Source | Short SHA |
| Image | Tag and short Digest |
| Status | Success/failure, Exit Code, Write Count |

## 15. Documentation Update Rules

### 15.1 README.md

Update only the necessary parts when the following change.

- Service responsibilities and boundaries with other MS
- Primary entrypoints and execution flow
- Input/output table contracts
- Configuration and environment variables
- common dependency and adapter structure
- Docker CMD and container execution method
- External dependencies or safety constraints

### 15.2 CHANGELOG.md

- Record only actual changes by date.
- Preserve past-time records of worklog creation, file deletion, and DB externalization as facts at the time.
- Distinguish documentation restructuring from Python functional changes.
- Do not record DB, AWS, or order validation that was not actually executed as complete.
- Repeated execution-prohibition sentences may be consolidated concisely into a per-date Security or Notes table.

### 15.3 docs/source-file-catalog.md

When the following changes are confirmed, update the related rows or sections together.

| Change | Update Content |
|---|---|
| File creation/deletion/rename | File list and roles |
| entrypoint change | Execution risk and call relationships |
| loader/repository responsibility change | Input/output and DB impact |
| common dependency change | Common functions and adapter responsibility |
| table/status contract change | Primary input/output and downstream impact |
| Docker/wrapper change | Execution image and operational wrapper role |
| Document creation/deletion | Documents list and roles |

If only the internal implementation changes and the file responsibility and change impact are the same, do not modify the catalog.
The catalog is not a full file inventory but a responsibility document for operationally and maintenance-important items.

### 15.4 Worklog

- Do not create `docs/worklog` and date-specific worklogs anew.
- Preserve past worklog-creation history remaining in the CHANGELOG as facts at the time; do not delete it.
- Leave only the necessary key changes for the current work history in the CHANGELOG.

## 16. Documentation Consistency

The four documents must use the same terminology and responsibility boundaries.

| Term | Basis |
|---|---|
| Service name | `port_strategy_decision` |
| Layer name | Decision |
| upstream | Preprocessor |
| downstream | StrategyExecution |
| Market decision | market decision |
| Buy artifact | daily BUY signal |
| Blocked market | BLOCK |
| Watch artifact | block watch candidate |
| Position decision | HOLD, SELL, SKIP |
| Reference date | Distinguish run date and data date |
| Storage method | Specifically denote insert, update, delete, upsert |
| External operations | Separate Scheduler, Step Functions, ECS RunTask from repository facts |

Do not add states, tables, columns, or operational structures that are not confirmed in code merely for documentation convenience.

## 17. Git Rules

- Preserve user changes before and after work.
- Use `git status --short` and `git diff --stat` only to confirm the change scope.
- Where possible, confirm whitespace errors with `git diff --check`.
- Do not run `git add`, `commit`, `push`, `reset`, `restore`, `checkout` without an explicit request.
- For attached-file work without a repository, do not report as if Git validation was performed.

## 18. Completion Conditions

Confirm the following before completing work.

- Were only the target files modified?
- Were the Decision responsibilities and boundaries with other MS preserved?
- Were the total feature input and strategy output contracts preserved?
- Were the meanings of BUY, BLOCK watch, HOLD, SELL, and SKIP not confused?
- Was the difference between v1 and v2 evaluators preserved?
- Were the common public contracts not changed arbitrarily?
- Were the DB write and re-run risks confirmed?
- Are the document roles and terminology consistent across the four documents?
- Was it confirmed whether the source catalog update conditions apply?
- Was no new worklog created?
- Was no verbatim sensitive information newly recorded?
- Were UTF-8 No BOM, the 300-character cell, and the 500-character line standards met?
- Was validation that was not executed not reported as successful?

## 19. Completion Report

Write the completion report concisely, centered on two-column tables.

| Item | Report Content |
|---|---|
| Changed files | Actually modified files |
| Change summary | Key changes to responsibilities, contracts, and document structure |
| Validation result | Static checks and safe validation performed |
| Not performed | Unexecuted items related to DB, AWS, signal, and orders |
| Remaining risk | Items requiring code comparison or operational confirmation |
| Sensitive information | Whether verbatim was newly recorded |

Actual operational execution beyond documentation changes is performed only when the user explicitly requests and approves it.
