# port_strategy_decision

`port_strategy_decision` is the Decision microservice that reads the total feature produced by the Preprocessor and generates daily strategy decisions.

It judges the market state and the allowable buy range, filters stock candidates, and computes quantities. It also evaluates active positions to generate HOLD, SELL, and SKIP decisions.

This document describes the current repository file structure and the validated operational AS-IS. On 2026-07-31, within the approved DevOps scope, the AWS Shadow Canary and the operational Step 6/7 E2E were executed. On 2026-08-10, the Decision Comparison that automatically compares operational DB results against Shadow JSON, together with the GitHub `production` approval-based Production Promotion, were validated. Step 8 onward, StrategyExecution, and orders were not executed. This documentation update task itself performs no additional AWS, DB, or order execution.

## 1. Service Summary

| Item | Value |
|---|---|
| Service | `port_strategy_decision` |
| Layer | Daily Decision |
| Primary input | `pre_total_market_daily_feature`, `pre_total_stock_daily_feature` |
| Primary decisions | Market, Buy Filter, Sizing, BUY, BLOCK Watch, HOLD, SELL, SKIP |
| Primary output | Daily Run, Daily Signal, Block Watch Candidate, Position Decision, Position State |
| Common logic | `port_strategy_common` 1.0.0 Wheel |
| Operational entrypoints | `daily_buy_signal_run.py`, `daily_position_signal_run.py` |
| Execution modes | Operational mode and read-only `--shadow` Shadow Canary mode |
| Repository | `wooktae/port-strategy-decision`, default branch `main` |
| CI/deployment | GitHub Actions → CodeBuild → Candidate Shadow → Comparison → `production` approval → Production Promotion |
| Detailed file document | `docs/source-file-catalog.md` |

## 2. Responsibility Boundary

Decision generates and stores decision results based on features. Source collection, feature generation, order execution, and view presentation are the responsibility of other layers.

### 2.1 Scope Owned by Decision

| Area | Responsibility |
|---|---|
| Market | Judge the market state and exposure limits, maximum position count, and minimum score/flow criteria |
| Buy Filter | Filter stock features against buy candidate criteria |
| Sizing | Compute the buy quantity and weight per candidate |
| Daily Buy | Generate the Daily Run and BUY Signal and update execution status |
| BLOCK Watch | Separately record watch candidates during a BUY-blocked regime |
| Position | Judge HOLD, SELL, and SKIP for active positions |
| Adapter | Convert `port_strategy_common` results into the daily storage format |

### 2.2 Scope Owned by Other Layers

| Area | Owning Layer |
|---|---|
| External data collection | Crawler |
| raw data preprocessing and total feature generation | Preprocessor |
| execution plan and order request composition | StrategyExecution |
| broker order/fill/balance/holding synchronization | MarketConnector |
| backtest scenarios and research reports | StrategyResearch |
| status query and approval UI | View |
| full batch orchestration | EventBridge Scheduler and Step Functions |
| image build, ECR push, and task definition registration | Deployment pipeline |

Even when Decision produces a SELL decision, it does not submit an actual sell order. A BUY Signal is likewise not an order until StrategyExecution consumes it.

## 3. Core Execution Flow

Operational mode stores decision results in the DB. `--shadow` mode reuses the same input read-only and only outputs the results. Sections 3.1–3.3 describe the operational flow and 3.4 describes the Shadow Canary.

### 3.1 Daily Buy Signal

```text
Preprocessor total feature
  → Daily Feature Loader
  → Market Decision
  → Buy Candidate Filter
  → Position Sizing
  → BUY Signal or BLOCK Watch
  → Daily Run status update
```

| Stage | Primary File |
|---|---|
| entrypoint | `daily_buy_signal_run.py` |
| feature load | `daily_feature_loader.py` |
| market decision | `backtest_market.py` |
| candidate filter | `backtest_filter.py` |
| quantity calculation | `backtest_sizing.py` |
| signal conversion | `daily_signal_builder.py` |
| run/signal storage | `daily_repository.py` |
| BLOCK candidate selection | `daily_block_watch_builder.py` |
| BLOCK candidate storage | `daily_block_watch_repository.py` |

When Market is BLOCK, no general BUY Signal is created and only watch candidates are stored separately. Block Watch is a watch artifact, not an order-bypass path.

### 3.2 Daily Position Signal

```text
Latest completed Daily Run
  + Active Strategy Position
  + Broker Position Snapshot
  + Market·Stock Feature
  → Position Evaluator v1 or v2
  → HOLD · SELL · SKIP Decision
  → Position State latest evaluation update
```

| Stage | Primary File |
|---|---|
| entrypoint | `daily_position_signal_run.py` |
| v1 evaluation | `daily_position_evaluator.py` |
| v2 evaluation | `daily_position_evaluator_v2.py` |
| input query/result storage | `daily_position_repository.py` |

v1 directly evaluates the daily operational criteria. v2 first performs daily validation and then reuses the sell decision from `port_strategy_common`, converting it into the daily decision format.

### 3.3 Query and Auxiliary Entrypoints

| File | Current Role |
|---|---|
| `backtest_decision_run.py` | Auxiliary entrypoint that reads a single-day feature and outputs a market, filter, and sizing snapshot |
| `daily_validator.py` | Validation candidate that queries and inspects the latest Daily Run and Signal |

Both files may trigger DB queries. Do not run them during documentation work or simple structure inspection.

### 3.4 Shadow Canary Execution Mode

The operational entrypoints support a read-only Shadow Canary mode via the `--shadow` option.

| Item | Value |
|---|---|
| BUY Shadow | `daily_buy_signal_run.py --shadow` |
| Position Shadow | `daily_position_signal_run.py --shadow --evaluator-version v2` |
| Transaction | read-only, DB write blocked |
| Result | write_count=0 and CloudWatch structured JSON |
| Input | Same run date/data date and Preprocessor Feature as operations |
| Order linkage | Not linked to StrategyExecution/order paths |

Do not include `--shadow` in operational Commands. Shadow reuses the same input and computation path but does not store results; it only outputs them as JSON.

## 4. Input Data

Decision does not directly collect source data or generate the total feature.

| Input | Purpose |
|---|---|
| `pre_total_market_daily_feature` | Market state and market-level limit decision |
| `pre_total_stock_daily_feature` | Stock filter, sizing, and position evaluation |
| `stock_universe` | LEFT JOIN target for enriching the company name (company_name) |
| `connector_balance_snapshot` | Confirm the latest broker snapshot reference date in position evaluation |
| `connector_position_snapshot` | Confirm broker holding state |
| `strategy_position_state` | Confirm the latest state of the strategy position |

In input data, run date and data date are distinguished. You must confirm that the Market and Stock feature point to the same decision reference date, and a missing value must not be treated as equivalent to an actual 0 value.

## 5. Output Data

| Output | Meaning |
|---|---|
| `strategy_daily_run` | Daily Buy decision execution unit and final status |
| `strategy_daily_signal` | BUY candidates and sizing results |
| `strategy_block_watch_candidate` | Watch candidates in a BLOCK market |
| `strategy_daily_position_decision` | HOLD, SELL, SKIP decision history for positions |
| `strategy_position_state` | Latest evaluated state of a position |

Table names, status values, reasons, evaluator versions, unique keys, and upsert scope are connected to downstream contracts. When changing them, also confirm the impact on StrategyExecution and operational queries.

## 6. Primary File Structure

### 6.1 Daily Buy Group

| File | Role |
|---|---|
| `daily_buy_signal_run.py` | Entrypoint that ties together Market, Filter, Sizing, BUY, and BLOCK Watch |
| `daily_feature_loader.py` | Query run date, data date, and market/stock feature |
| `daily_signal_builder.py` | Convert sizing results into the Daily Signal storage format |
| `daily_repository.py` | Create, query, and update status for Daily Run and Signal |
| `daily_block_watch_builder.py` | Select watch candidates during a BLOCK regime |
| `daily_block_watch_repository.py` | Store Block Watch candidates and clean up the target scope |

### 6.2 Daily Position Group

| File | Role |
|---|---|
| `daily_position_signal_run.py` | Entrypoint for active position evaluation |
| `daily_position_evaluator.py` | Position Decision v1 |
| `daily_position_evaluator_v2.py` | v2 based on daily validation and common sell reuse |
| `daily_position_repository.py` | Query position/snapshot/feature and store Decision |

### 6.3 Common Decision Adapters

| File | Role |
|---|---|
| `backtest_market.py` | Convert the Common Market decision into the Decision format |
| `backtest_filter.py` | Adapter that calls the Common Buy Filter |
| `backtest_sizing.py` | Adapter that calls Common Position Allocation |
| `backtest_decision_run.py` | Auxiliary entrypoint for a single-day Decision Snapshot |

The input/output, DB access, and change impact of all files are managed in `docs/source-file-catalog.md`. Small helpers and local dumps are not assumed to be part of the primary structure until their operational responsibility is confirmed.

## 7. `port_strategy_common` Dependency

A significant portion of Decision's core decision logic reuses `port_strategy_common`.

| Area | Primary Contract |
|---|---|
| Config | Strategy Name, Engine Version, Market/Filter/Sizing settings and Snapshot |
| Market | Market Context and Market Decision |
| Buy Filter | Buy Candidate Filter |
| Sizing | Position Allocation |
| Guard | Buy Guard and Size Haircut |
| BLOCK Watch | Block Watch Candidate evaluation |
| Sell | Common Backtest Sell Decision |

The primary usage relationships confirmed in the current documentation are as follows.

| File | Common Usage |
|---|---|
| `backtest_market.py` | `common_decide_market` |
| `backtest_filter.py` | `common_filter_buy_candidates` |
| `backtest_sizing.py` | `common_allocate_positions` |
| `daily_buy_signal_run.py` | Buy Guard, Size Haircut, Safe Float |
| `daily_block_watch_builder.py` | Block Watch Candidate evaluation |
| `daily_position_evaluator_v2.py` | `common_evaluate_backtest_sell` |

Public function names, dataclass fields, enums, config keys, and reason strings may be connected to other services. Do not change them based on a Decision-only decision.

## 8. AWS Paper Daily Position

Decision is used as a decision stage within AWS Paper Daily. The detailed implementation of the Scheduler, Step Functions states, and Lambdas is managed by each owning repository.

| Daily Stage | Decision Role |
|---|---|
| Step 6 · Daily Buy Signal | Read the total feature and store the Market, Filter, Sizing, BUY, or BLOCK Watch result |
| Step 7 · Position Signal | Read active positions and store the HOLD, SELL, SKIP Decision |

### 8.1 Step 6

| Item | Value |
|---|---|
| entrypoint | `daily_buy_signal_run.py` |
| Input | Market/Stock Total Feature, Universe, and decision settings |
| Output | Daily Run, Daily Signal, or Block Watch Candidate |
| Not done directly | Execution Plan generation, order requests, and broker order submission |

### 8.2 Step 7

| Item | Value |
|---|---|
| entrypoint | `daily_position_signal_run.py` |
| Input | Latest Completed Run, Active Position, Broker Snapshot, Feature |
| Output | Position Decision and Position State latest evaluation |
| Not done directly | Sell order request generation and broker order submission |

### 8.3 Shadow Canary

Shadow Canary is a read-only validation path separated from operations. It uses a dedicated Shadow Family separate from the operational BUY/Position Family.

| Item | Value |
|---|---|
| BUY Shadow Family | Dedicated ECS Task Definition Family separated from operations |
| Position Shadow Family | Dedicated ECS Task Definition Family separated from operations |
| BUY Shadow Command | `--shadow` added to the operational entrypoint |
| Position Shadow Command | `--shadow --evaluator-version v2` |
| Execution order | BUY Shadow → Position Shadow, sequential |
| Storage contract | read-only, write_count=0 |
| Result | CloudWatch structured JSON |
| Order linkage | Separated from StrategyExecution/order paths |

The current Production Promotion Workflow registers a new Revision of the Shadow Family with the Candidate Image, and the GitHub Workflow runs BUY Shadow and Position Shadow directly via ECS RunTask. A separate `portfolio-paper-decision-shadow-canary` State Machine exists as an existing Shadow validation resource but is not the Candidate execution agent in the current Promotion Workflow. The one-time Shadow Revision number created during Candidate execution is not recorded as a fixed value in documentation.

### 8.4 Operational Promotion and Rollback

| Item | Value |
|---|---|
| Promotion target | Operational BUY/Position Task Definition |
| Operational Command | No Shadow option, existing operational logic retained |
| BUY operational Command | `daily_buy_signal_run` |
| Position operational Command | Default v1 `daily_position_signal_run` |
| Promotion Image | Uses the approved identical Candidate Image without rebuild |
| Candidate Image Tag | Git SHA-based `a01d90592a7c` |
| Referencing State Machines | 5 operational State Machines that reference the Decision Revision |
| Transition basis | Register/transition a new Revision from the existing operational `:3` baseline, and confirm removal of the previous `:3` reference |

On 2026-07-31, the Rollback path was validated by `:2`→`:3` promotion, `:3`→`:2` Rollback, and `:2`→`:3` re-promotion. The final Production Promotion on 2026-08-10 registered the approved Candidate Image as a new Revision from the existing operational `:3` baseline, transitioned the references of the 5 operational State Machines, and then validated removal of the previous `:3` reference. The actual current operational Revision number is confirmed from the live AWS state and is not recorded in documentation as a presumed fixed value.

### 8.5 Operational Step 6/7 E2E Status

| Item | Value |
|---|---|
| BUY E2E | Step 6 dedicated State Machine execution SUCCEEDED |
| Position E2E | Step 7 dedicated State Machine execution SUCCEEDED |
| Executed Revision | Operational BUY/Position Revision `:3` |
| Container | Both executions Exit Code 0 |
| Image | Expected Tag/Digest match |
| Log | CloudWatch confirmed, 0 error patterns |
| Execution scope | Only Step 6/7 executed; Step 8 onward, StrategyExecution, and orders not executed |

This E2E is validation up to the Decision stage; it is not the full Paper Daily Step 1–17 or order fill validation. At execution time the input was BLOCK and there were 0 positions, so the result was 0 records; this is not a validation failure but a normal result given the input conditions.

The actual cluster, task definition ARN, image URI, subnet, security group, command id, and credentials are not recorded in the README.

### 8.6 Decision Comparison

On 2026-08-10, the Decision Comparison that automatically compares operational DB results against the Shadow CloudWatch JSON was performed with real data.

| Item | Value |
|---|---|
| Comparison agent | `decision_comparator.py` |
| ECS execution wrapper | `decision_comparison_ecs_run.py` |
| Comparison targets | Operational Daily Run results (BUY/Position) and Shadow JSON |
| DB impact | Operational DB read-only query, no new Decision result storage |
| Four result types | MATCH, DIFFERENCE, REVIEW_REQUIRED, INVALID |

| Result | Meaning |
|---|---|
| MATCH | No meaningful difference |
| DIFFERENCE | Valid but with detailed value differences |
| REVIEW_REQUIRED | A difference that a human must review, such as a decision change |
| INVALID | The comparison itself cannot be trusted, so not a Promotion candidate |

The 2026-08-10 real-data result was: Market was BLOCK for both operations and Shadow, hence MATCH; 0 BUY Shadow Signals; 3 Shadow Position Decisions; write_count=0; and the final result was `REVIEW_REQUIRED`. The automatic Comparison actually detected a real-data difference and forwarded it to the Review Gate. This difference includes the operational v1 vs Shadow v2 difference and the active position population difference at execution time, and does not mean that the Candidate code incorrectly changed the operational decision. `INVALID` is not treated as a normal Comparison result and blocks Promotion.

## 9. Container Image and CI/Deployment Pipeline

`Dockerfile` defines the Decision execution image, and `.devops` and `.github/workflows` own the CI/deployment path.

### 9.1 Container Image

| Item | Value |
|---|---|
| Base Image | Python 3.13 slim |
| Default CMD | `python -m port_strategy_decision.daily_buy_signal_run` |
| Position execution | Specify `daily_position_signal_run` via container command override |
| Common inclusion | Install `port_strategy_common` 1.0.0 Wheel |
| Deployment responsibility | Separate deployment pipeline |

### 9.2 `port_strategy_common` Installation Structure

The current image does not vendor `port_strategy_common`; it installs the validated 1.0.0 Wheel.

| Item | Value |
|---|---|
| Package version | 1.0.0 |
| Wheel preparation | Fetched from CodeArtifact and placed in `.devops/packages` |
| Install timing | `--no-deps` install during Docker Build |
| Wheel tracking | `.devops/packages/*.whl` is a git-ignored build artifact |
| Contract validation | import/contract test from the Decision Consumer perspective |

The full CodeArtifact Domain/Repository/endpoint identifiers are not recorded in documentation.

### 9.3 CI Quality Gates

`.devops/codebuild/buildspec.yml` performs the following quality gates in order.

| Stage | Content |
|---|---|
| Python Compile | `compileall` |
| Unit/Contract Test | `pytest` (import contract, position evaluator version contract) |
| Static Analysis | Ruff |
| Host Import Smoke | `.devops/scripts/container-smoke.py` |
| Host Entrypoint Smoke | `.devops/scripts/entrypoint-smoke.py` |
| Docker Build | image build |
| Container Import Smoke | in-container import smoke |
| Container Entrypoint Smoke | in-container entrypoint smoke |
| ECR Push | Performed only when `PUSH_IMAGE=true` |

`PUSH_IMAGE=false` performs only the quality gates and skips the push. `PUSH_IMAGE=true` performs ECR push and Digest confirmation after validation.

### 9.4 GitHub Actions and Release Flow

| Item | Value |
|---|---|
| Workflow | `.github/workflows/decision-codebuild.yml` |
| Trigger | `workflow_dispatch` |
| Authentication | GitHub OIDC (main branch trust) |
| Source | Pass the GitHub Commit SHA as the CodeBuild Source Version |
| Approval | GitHub `production` Environment manual approval |

The current Workflow is not a simple CodeBuild trigger; it owns the flow below.

```text
workflow_dispatch
  → GitHub OIDC
  → Decision CodeBuild (Git SHA Candidate Image)
  → Register Candidate BUY/Position Shadow Task Definition
  → Run ECS BUY Shadow → Position Shadow
  → Collect CloudWatch Shadow JSON
  → Run ECS Comparator
  → Collect Comparison Report and generate GitHub Job Summary
  → production Environment manual approval
  → Production Promotion on approval
  → Register new operational BUY/Position Revision
  → Transition and validate references of 5 operational State Machines
```

On Reject, Promotion does not run, and an `INVALID` Comparison cannot proceed to the approval stage. Entrypoint Smoke runs only the argparse `--help` path and does not call the DB connection or the operational run functions. Detailed IAM Policy, OIDC subject text, full ARNs, subnet, security group, account ID, and execution ID are not recorded in documentation.

## 10. How to Run

Since internal imports use the `from port_strategy_decision.xxx import ...` form, use the `python -m` form rather than running a file path directly.

The commands below are examples to illustrate the execution form. Because DB queries and writes may occur, do not run them during documentation work.

```powershell
python -m port_strategy_decision.daily_buy_signal_run `
  --run-date 2026-05-26 `
  --data-date 2026-05-25

python -m port_strategy_decision.daily_position_signal_run `
  --evaluator-version v2

python -m port_strategy_decision.daily_position_signal_run `
  --validate-only

python -m port_strategy_decision.daily_buy_signal_run `
  --shadow

python -m port_strategy_decision.daily_position_signal_run `
  --shadow `
  --evaluator-version v2

python -m port_strategy_decision.daily_validator
```

`daily_buy_signal_run` supports `--run-date`, `--data-date`, `--note`, and `--shadow`. `daily_position_signal_run` supports `--account-no`, `--validate-only`, `--shadow`, and `--evaluator-version {v1,v2}`, with a default of `v1`.

| Entrypoint | Execution Impact |
|---|---|
| `daily_buy_signal_run` | Can create/update Daily Run, Signal, and Block Watch data |
| `daily_buy_signal_run --shadow` | read-only, outputs JSON results without DB write |
| `daily_position_signal_run` | Can update Position Decision and Position State |
| `daily_position_signal_run --shadow` | read-only, outputs JSON results without DB write |
| `daily_validator` | Can query the DB and output data |
| `backtest_decision_run` | Can query DB features even though it does not create a Run record |

## 11. Configuration

Configuration uses `port_strategy_common.config` and the local `db_config.py`.

### 11.1 Primary Configuration Areas

| Setting | Purpose |
|---|---|
| PostgreSQL connection | host, port, database, user, and password |
| Strategy settings | Strategy Name and Engine Version |
| Market settings | Market state and exposure limit decision |
| Filter settings | Buy candidate criteria |
| Sizing settings | Weight and quantity calculation per candidate |
| Decision Run Date | Candidate override for the execution reference date |
| Schema contract | Interpretation of Feature input and Strategy output tables |

### 11.2 DB Environment Variables

The current documentation and the `db_config.py` contract are based on the `INTEREST_DB_*` family.

```powershell
$env:INTEREST_DB_HOST="localhost"
$env:INTEREST_DB_PORT="5433"
$env:INTEREST_DB_NAME="portfolio"
$env:INTEREST_DB_USER="postgres"
$env:INTEREST_DB_PASSWORD="[REDACTED]"
```

| Environment Variable | Per Current Documentation |
|---|---|
| `INTEREST_DB_HOST` | Default `localhost` |
| `INTEREST_DB_PORT` | Default `5433` |
| `INTEREST_DB_NAME` | Default `portfolio` |
| `INTEREST_DB_USER` | Default `postgres` |
| `INTEREST_DB_PASSWORD` | No default; execution error if missing |

Actual credentials are managed via environment variables or a local secret loader. Passwords, tokens, accounts, and webhook URLs are not left verbatim in documentation or logs.

### 11.3 Search Path

Per the current documentation, the DB connection search path uses the following order.

```text
decision, research, preprocessor, execution, connector, reference, legacy, public
```

| Schema | Primary Role |
|---|---|
| `decision` | Daily Run, Signal, and Position Decision |
| `research` | Block Watch Candidate |
| `preprocessor` | Market/Stock Total Feature |
| `execution` | Downstream execution contract reference |
| `connector` | Balance and Position Snapshot |
| `reference` | Reference information such as Stock Universe |
| `legacy`, `public` | Compatibility with existing unqualified SQL |

Because of the use of `strategy_block_watch_candidate`, the `research` schema is included in the search path. Changing the order can change the target table of unqualified SQL, so it is treated as a contract change.

## 12. External Dependencies

| Dependency | Purpose |
|---|---|
| Python | Runtime |
| PostgreSQL | Feature query and Decision storage |
| `psycopg2` | PostgreSQL connection |
| `psycopg2.extras` | Row and Batch processing support |
| `port_strategy_common` | Common decisions for Market, Filter, Sizing, Guard, and Sell |
| Preprocessor Feature | Decision input |
| Connector Snapshot | Position evaluation input |
| StrategyExecution | Downstream consumer of the Daily Signal |

For the exact installed versions of dependencies and the deployment configuration, check `requirements.txt`, the Dockerfile, and the deployment repository together.

## 13. State and Re-run Cautions

| Caution | Item to Confirm |
|---|---|
| Partial success | Confirm the Run is not marked successful after only some rows are stored |
| Re-run | Confirm duplicate/residual rows for the same run date and data date |
| Transaction | Confirm the commit boundary for delete, insert, upsert, and status updates |
| Missing feature | Confirm a missing value is not mistaken for an actual 0 value |
| Position consistency | Compare ticker/quantity between the Strategy Position and the Broker Position |
| Status strings | Preserve the meaning of BUY, BLOCK, HOLD, SELL, SKIP, and reason |
| Version | Preserve Evaluator Version and Engine Version |

Do not conclude from the README alone that the current implementation automatically blocks all partial failures. In an actual change or incident analysis, you must confirm the exception propagation, commit, and final status handling in the entrypoint and repository.

## 14. Document Structure

| Document | Role |
|---|---|
| `AGENTS.md` | Kiro work scope, safety, data contracts, and validation rules |
| `README.md` | Current service structure, flow, execution/configuration, and operational position |
| `CHANGELOG.md` | Primary change history and facts at the time |
| `docs/source-file-catalog.md` | Role, input/output, and change impact of operationally important files |

When file responsibilities, entrypoints, DB access, Common dependencies, or operational wrappers change, check the README and `docs/source-file-catalog.md` together. Do not create new date-specific worklog documents.

## 15. Safe Validation Scope

When only documentation is modified, confirm only the changed files and diff scope.

```powershell
git status --short
git diff --stat
```

Even for code changes, prioritize validation that involves no actual Daily Signal, Position Signal, backtest, DB write, external API, AWS, or order execution. Validation that requires operational execution is not performed automatically and is reported as remaining validation.
