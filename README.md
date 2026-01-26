# Dim-Mod-Sim

A simulation framework for testing dimensional modeling skills. Generates synthetic retail shops with random but internally consistent business rules, emits event logs, produces natural-language descriptions, and evaluates dimensional model submissions.

## Installation

```bash
poetry install
```

## Quick Start

```bash
# Generate a shop scenario (config, events, description)
poetry run dim-mod-sim generate --seed 42 --difficulty medium

# View the generated shop configuration
poetry run dim-mod-sim info output/shop_config.json

# Create your dimensional model schema (see Schema Format below)
# Then evaluate it:
poetry run dim-mod-sim evaluate output/shop_config.json output/events.json my_schema.json
```

## Commands

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

### evaluate

Score a dimensional model submission against a generated shop.

```bash
poetry run dim-mod-sim evaluate SHOP_CONFIG EVENTS SCHEMA [OPTIONS]

Options:
  --output PATH      Output path for report
  --format TEXT      rich | json | markdown (default: rich)
```

**Evaluation Axes (0-100 each):**
- **Event Preservation** - Can every event be represented without loss?
- **Grain Correctness** - Do fact tables respect a single declared grain?
- **Temporal Correctness** - Can historical queries be answered correctly?
- **Semantic Faithfulness** - Does the model reflect shop rules?
- **Structural Optimality** - No unnecessary complexity?
- **Queryability** - Bonus for good query patterns

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

```bash
# 1. Generate an adversarial scenario
poetry run dim-mod-sim generate --seed 123 --difficulty adversarial --num-events 5000

# 2. Read the description to understand the business rules
cat output/description.md

# 3. Design your dimensional model based on the description
vim my_schema.json

# 4. Validate your schema structure
poetry run dim-mod-sim validate-schema my_schema.json

# 5. Evaluate your model
poetry run dim-mod-sim evaluate output/shop_config.json output/events.json my_schema.json

# 6. Iterate based on feedback
```

## Determinism

All generation is deterministic given a seed. Running the same command twice with the same seed produces identical output.
