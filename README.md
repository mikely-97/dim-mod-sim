# Dim-Mod-Sim

A simulation framework for testing dimensional modeling skills. Generates synthetic retail shops with random but internally consistent business rules, emits event logs, produces natural-language descriptions, and evaluates dimensional model submissions.

## Installation

```bash
poetry install
```

## Quick Start

The recommended way to use Dim-Mod-Sim is the interactive `play` command:

```bash
# Start an interactive session with adversarial framing
poetry run dim-mod-sim play --seed 42 --difficulty medium
```

This will:
1. Generate a shop scenario with "traps" highlighted
2. Create a schema scaffold with TODOs for you to complete
3. Let you iterate on your schema with actionable feedback
4. Track your progress across attempts

Alternatively, use individual commands for more control:

```bash
# Generate a shop scenario (config, events, description)
poetry run dim-mod-sim generate --seed 42 --difficulty medium

# Generate a schema scaffold to start from
poetry run dim-mod-sim scaffold output/shop_config.json

# Evaluate your dimensional model
poetry run dim-mod-sim evaluate output/shop_config.json output/events.json my_schema.json

# Get concrete examples of where your model fails
poetry run dim-mod-sim explain output/shop_config.json output/events.json my_schema.json
```

## Commands

### play

**Primary entry point.** Orchestrates the full interactive modeling experience.

```bash
poetry run dim-mod-sim play [OPTIONS]

Options:
  --seed INTEGER              Random seed (auto-generated if not provided)
  --difficulty TEXT           easy | medium | hard | adversarial (default: medium)
  --output-dir PATH           Output directory (default: ./output)
  --num-events INTEGER        Number of events to generate (default: 1000)
  --simulation-days INTEGER   Maximum simulation days (default: 30)
  --scaffold / --no-scaffold  Generate schema scaffold (default: True)
```

The play command:
1. Displays a **difficulty briefing** showing enabled "traps" (modeling challenges)
2. Generates shop config, events, and description
3. Optionally creates a **schema scaffold** with TODOs
4. Runs an evaluation loop until you quit
5. **Tracks progress** locally for improvement/regression feedback

Example output:
```
╭─────────────────────────────────────────────────────────────────╮
│                   ADVERSARIAL SCENARIO                          │
│  Seed: 42  |  Shop: Quick Depot  |  Events: 1,000               │
╰─────────────────────────────────────────────────────────────────╯

Quick Depot will try to break your model.

╭─ Traps Enabled ─────────────────────────────────────────────────╮
│  GRAIN                                                          │
│    ⚠ Mixed transaction grain (some receipts, some line items)   │
│    ⚠ Multiple payments per transaction                          │
│                                                                 │
│  TEMPORAL                                                       │
│    ⚠ Business date differs from timestamp                       │
│    ⚠ Backdated corrections allowed                              │
╰─────────────────────────────────────────────────────────────────╯
```

### scaffold

Generate a schema skeleton with TODOs based on the shop configuration.

```bash
poetry run dim-mod-sim scaffold SHOP_CONFIG [OPTIONS]

Options:
  --output PATH    Output path for scaffold (default: ./scaffold.json)
```

The scaffold provides:
- Fact and dimension table structures
- **Intentionally questionable defaults** (e.g., Type 1 SCD when Type 2 is needed)
- `_todo` and `_warning` annotations highlighting modeling decisions
- A starting point that requires thought, not a correct solution

Example scaffold output:
```json
{
  "fact_tables": [{
    "name": "fact_sales",
    "grain_description": "TODO: Define grain - consider mixed transaction levels",
    "_todo": "Multiple payments enabled - consider separate payment fact"
  }],
  "dimension_tables": [{
    "name": "dim_product",
    "scd_strategy": "type_1",
    "_warning": "Product hierarchy changes FREQUENTLY - consider Type 2"
  }]
}
```

### evaluate

Score a dimensional model submission against a generated shop.

```bash
poetry run dim-mod-sim evaluate SHOP_CONFIG EVENTS SCHEMA [OPTIONS]

Options:
  --output PATH      Output path for report
  --format TEXT      actionable | rich | json | markdown (default: actionable)
```

**Evaluation Axes (0-100 each):**
- **Event Preservation** - Can every event be represented without loss?
- **Grain Correctness** - Do fact tables respect a single declared grain?
- **Temporal Correctness** - Can historical queries be answered correctly?
- **Semantic Faithfulness** - Does the model reflect shop rules?
- **Structural Optimality** - No unnecessary complexity?
- **Queryability** - Bonus for good query patterns

**Actionable Format (default):**

The `actionable` format groups violations by type and provides concrete examples, consequences, and fix hints:

```
╭─────────────────────────────────────────────────────────────────╮
│  EVALUATION: 52/100 (52.0%)                                     │
│  3 grain violations | 2 temporal lies | 1 semantic mismatch     │
╰─────────────────────────────────────────────────────────────────╯

╭─ GRAIN VIOLATIONS ──────────────────────────────────────────────╮
│  [CRITICAL] Mixed grain in single fact table                    │
│                                                                 │
│  Example: TXN-001 has 3 line items; TXN-002 is receipt-level    │
│                                                                 │
│  Consequence: SUM(quantity) will double-count or lose items     │
│                                                                 │
│  Fix: Split into fact_sales_line and fact_sales_receipt         │
╰─────────────────────────────────────────────────────────────────╯
```

### explain

Show concrete scenarios where your model produces wrong answers.

```bash
poetry run dim-mod-sim explain SHOP_CONFIG EVENTS SCHEMA [OPTIONS]

Options:
  --verbose    Show detailed event traces
```

The explain command generates **query scenarios** that demonstrate specific failures:

```
╭─ Scenario: The Backdated Correction ────────────────────────────╮
│  Business Question: "What were total sales on January 15th?"    │
│                                                                 │
│  What Actually Happened:                                        │
│  - TXN-500 recorded on Jan 15 for $100                          │
│  - On Jan 20, manager corrected TXN-500 to $150                 │
│  - Correction is backdated to be effective Jan 15               │
│                                                                 │
│  Expected Answer: $150                                          │
│  Your Model Returns: $100 (or $250 if you count both)           │
│                                                                 │
│  Why It's Wrong:                                                │
│  Your fact_sales has no business_effective_date column.         │
│  The correction has event_timestamp = Jan 20, but               │
│  business_effective_date = Jan 15. You can't distinguish.       │
╰─────────────────────────────────────────────────────────────────╯
```

### generate

Generate a complete shop scenario with configuration, events, and description.

```bash
poetry run dim-mod-sim generate [OPTIONS]

Options:
  --seed INTEGER          Random seed for deterministic generation
  --difficulty TEXT       easy | medium | hard | adversarial (default: medium)
  --output-dir PATH       Output directory (default: ./output)
  --num-events INTEGER    Number of events to generate (default: 1000)
  --simulation-days INT   Maximum simulation days (default: 30)
```

**Output files:**
- `shop_config.json` - Complete shop configuration
- `events.json` - Generated event log
- `description.md` - Human-readable business rules

### describe

Regenerate just the shop description from a configuration.

```bash
poetry run dim-mod-sim describe SHOP_CONFIG [--output PATH]
```

### validate-schema

Validate schema JSON structure without evaluation.

```bash
poetry run dim-mod-sim validate-schema SCHEMA_FILE
```

### info

Display shop configuration details.

```bash
poetry run dim-mod-sim info SHOP_CONFIG
```

## Progress Tracking

Dim-Mod-Sim tracks your progress locally for each (seed, difficulty) combination.

**Storage location:** `~/.dim-mod-sim/progress.json`

Override with environment variable: `DIM_MOD_SIM_PROGRESS_FILE`

Progress tracking provides:
- **Best score** achieved for each scenario
- **Attempt history** with improvement/regression indicators
- **Personal best** notifications when you beat your high score

Example progress display:
```
╭─ Progress: Seed 42, Medium ─────────────────────────────────────╮
│  Best Score: 78 (78.0%)                                         │
│  Attempts: 5                                                    │
│                                                                 │
│  Recent History:                                                │
│    #3  65.0%  ████████████████░░░░                              │
│    #4  72.0%  ██████████████████░░ +7%                          │
│    #5  78.0%  ███████████████████░ +6% BEST                     │
╰─────────────────────────────────────────────────────────────────╯
```

## Schema Submission Format

Submit your dimensional model as JSON:

```json
{
  "fact_tables": [
    {
      "name": "fact_sales",
      "grain_description": "One row per line item sold",
      "grain_columns": [
        {"name": "transaction_id", "is_degenerate": true},
        {"name": "line_number", "is_degenerate": true}
      ],
      "measures": [
        {"name": "quantity", "data_type": "int", "aggregation": "sum"},
        {"name": "amount", "data_type": "decimal", "aggregation": "sum"}
      ],
      "dimension_keys": ["date_key", "product_key", "store_key", "customer_key"]
    }
  ],
  "dimension_tables": [
    {
      "name": "dim_product",
      "natural_key": ["sku"],
      "surrogate_key": "product_key",
      "scd_strategy": "type_2",
      "attributes": [
        {"name": "product_name", "data_type": "varchar"},
        {"name": "category", "data_type": "varchar", "scd_tracked": true}
      ]
    }
  ],
  "relationships": [
    {
      "fact_table": "fact_sales",
      "dimension_table": "dim_product",
      "fact_column": "product_key",
      "dimension_column": "product_key"
    }
  ],
  "bridge_tables": []
}
```

### SCD Strategies

- `type_0` - Fixed, no changes
- `type_1` - Overwrite (current value only)
- `type_2` - Add row (full history)
- `type_3` - Add column (previous + current)
- `type_6` - Hybrid (1+2+3)
- `none` - No SCD handling

### Aggregation Types

`sum`, `count`, `min`, `max`, `avg`, `distinct_count`

## Difficulty Levels

| Level | Description |
|-------|-------------|
| **easy** | Line-item grain, reliable customer IDs, simple promotions |
| **medium** | Mixed features, some ambiguities |
| **hard** | Mixed grain, unreliable IDs, frequent hierarchy changes |
| **adversarial** | Maximum complexity, all modeling traps enabled |

Each difficulty level enables different combinations of "traps" that your model must handle correctly. The `play` command shows exactly which traps are enabled for your scenario.

## Violation Types

The evaluator categorizes issues into these types:

| Type | Description |
|------|-------------|
| **grain_violation** | Fact table grain is ambiguous or inconsistent |
| **temporal_lie** | Historical queries will return wrong results |
| **semantic_mismatch** | Model doesn't reflect actual business rules |
| **over_modeling** | Unnecessary complexity that adds no value |
| **under_modeling** | Missing structure needed for business requirements |
| **data_loss** | Events cannot be fully represented |
| **fan_out_risk** | Joins will produce duplicated or missing rows |

## Shop Configuration Dimensions

The generator randomly selects from these options:

- **Transactions**: grain (receipt/line-item/mixed), multiple payments, voids, manual overrides
- **Time**: timestamp vs business date, late-arriving events, backdated corrections
- **Products**: SKU reuse, hierarchy changes, bundles, virtual products
- **Customers**: anonymous allowed, ID reliability, household grouping
- **Stores**: physical/online channels, cross-store returns, lifecycle changes
- **Promotions**: per-line-item count, stackable, basket-level, post-transaction
- **Returns**: reference policy (always/sometimes/never), pricing policy
- **Inventory**: tracked, type (transactional/periodic/both)

## Example Workflow

### Interactive (Recommended)

```bash
# Start an interactive adversarial session
poetry run dim-mod-sim play --seed 123 --difficulty adversarial

# The play command will:
# 1. Show you what traps are enabled
# 2. Generate a scaffold to start from
# 3. Let you iterate with actionable feedback
# 4. Track your progress
```

### Manual

```bash
# 1. Generate an adversarial scenario
poetry run dim-mod-sim generate --seed 123 --difficulty adversarial --num-events 5000

# 2. Read the description to understand the business rules
cat output/description.md

# 3. Generate a scaffold to start from
poetry run dim-mod-sim scaffold output/shop_config.json

# 4. Edit the scaffold to complete your model
vim scaffold.json

# 5. Validate your schema structure
poetry run dim-mod-sim validate-schema scaffold.json

# 6. Evaluate your model with actionable feedback
poetry run dim-mod-sim evaluate output/shop_config.json output/events.json scaffold.json

# 7. See concrete examples of failures
poetry run dim-mod-sim explain output/shop_config.json output/events.json scaffold.json

# 8. Iterate based on feedback
```

## Determinism

All generation is deterministic given a seed. Running the same command twice with the same seed produces identical output.
