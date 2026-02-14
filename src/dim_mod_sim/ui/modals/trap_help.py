"""Trap help modal for detailed trap explanations."""

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Markdown, Static

from dim_mod_sim.play.framing import EnabledTrap, TrapCategory


# Detailed trap explanations
TRAP_DETAILS: dict[str, dict[str, str]] = {
    # Grain traps
    "mixed_grain": {
        "title": "Mixed Transaction Grain",
        "description": """
This shop records transactions at **different levels of detail**:
- Some transactions are recorded at the **receipt level** (one row per transaction)
- Others are recorded at the **line-item level** (one row per product purchased)

### Why This Breaks Models

If you create a single fact table, aggregations will be wrong:
- `SUM(quantity)` will double-count items on line-item transactions
- `COUNT(*)` will undercount receipts

### How to Handle It

1. **Separate fact tables**: Create `fact_receipt` and `fact_line_item`
2. **Grain indicator**: Add `is_line_item_level` boolean column
3. **Derived metrics**: Pre-aggregate line items when needed
""",
    },
    "multiple_payments": {
        "title": "Multiple Payment Methods",
        "description": """
This shop allows customers to **split payments** across multiple methods:
- Cash + Credit Card
- Gift Card + Cash
- Multiple credit cards

### Why This Breaks Models

A simple `payment_method` column on the transaction fact can't represent this.
Joining to a payments table without proper handling causes **fan-out**.

### How to Handle It

1. **Bridge table**: Create `bridge_transaction_payment`
2. **Payments fact**: Separate `fact_payment` table
3. **Payment allocation**: Track amount per payment method
""",
    },
    # Temporal traps
    "late_arriving_events": {
        "title": "Late-Arriving Events",
        "description": """
Events in this shop **arrive out of order**:
- Returns processed before the original sale is recorded
- Inventory adjustments backdated
- Customer updates applied retroactively

### Why This Breaks Models

If you use Type 1 SCD (overwrite), you lose the ability to answer:
- "What was the state when this event occurred?"
- "Why does this report differ from yesterday's run?"

### How to Handle It

1. **Type 2 SCD**: Track all historical changes with effective dates
2. **Event timestamp**: Distinguish event_time from load_time
3. **Late-arriving handling**: Process updates to historical records
""",
    },
    "backdated_corrections": {
        "title": "Backdated Corrections",
        "description": """
This shop allows **corrections to past data**:
- Price adjustments applied retroactively
- Quantity corrections for inventory errors
- Category reassignments with historical effect

### Why This Breaks Models

Without proper versioning, reports become inconsistent:
- Yesterday's report shows different numbers than today's
- Auditors can't reproduce historical reports

### How to Handle It

1. **Audit columns**: Track original_value, corrected_value, correction_date
2. **Snapshot tables**: Preserve point-in-time states
3. **Correction fact**: Separate table for corrections
""",
    },
    # Identity traps
    "unreliable_customer_id": {
        "title": "Unreliable Customer Identity",
        "description": """
Customer identification in this shop is **inconsistent**:
- Same customer has multiple IDs
- IDs merge when accounts are linked
- Anonymous purchases with no ID

### Why This Breaks Models

Customer metrics become unreliable:
- Lifetime value is fragmented across IDs
- Repeat purchase rate is understated
- Cohort analysis breaks down

### How to Handle It

1. **Master customer ID**: Resolve duplicates to canonical ID
2. **Customer bridge**: Map transaction IDs to master IDs
3. **Unknown customer**: Handle anonymous with surrogate key
""",
    },
    "household_grouping": {
        "title": "Household Grouping",
        "description": """
This shop tracks **household relationships**:
- Family members share loyalty accounts
- Purchases attributed to household, not individual
- Household composition changes over time

### Why This Breaks Models

Individual vs. household metrics conflict:
- Is this a new customer or new household member?
- How to attribute promotional response?

### How to Handle It

1. **Household dimension**: Separate from customer dimension
2. **Bridge table**: Many-to-many customer-household
3. **Effective dating**: Track membership periods
""",
    },
    # Semantic traps
    "sku_reuse": {
        "title": "SKU Reuse",
        "description": """
This shop **reuses SKU codes**:
- Discontinued products release their SKUs
- New products may get recycled SKUs
- Same SKU means different products at different times

### Why This Breaks Models

Product lookups return wrong data:
- Historical sales show current product name
- Category analysis mixes unrelated products

### How to Handle It

1. **Product key**: Use surrogate key, not SKU
2. **Effective dating**: Track SKU validity periods
3. **Type 2 SCD**: Full history of product attributes
""",
    },
    "hierarchy_changes": {
        "title": "Product Hierarchy Changes",
        "description": """
Product categorization **changes over time**:
- Products move between categories
- Category structure reorganizes
- New levels added to hierarchy

### Why This Breaks Models

Category reports are inconsistent:
- Same product in different categories depending on date
- Year-over-year comparisons break

### How to Handle It

1. **Type 2 SCD**: Track hierarchy history
2. **Bridge tables**: For many-to-many categories
3. **Conformed hierarchy**: Standardize across time
""",
    },
    # Relationship traps
    "cross_store_returns": {
        "title": "Cross-Store Returns",
        "description": """
Customers can **return items to different stores**:
- Buy online, return in store
- Buy at Store A, return at Store B
- Returns without receipts

### Why This Breaks Models

Store metrics become incorrect:
- Returning store shows negative sales
- Selling store doesn't reflect returns

### How to Handle It

1. **Return fact**: Separate from sales fact
2. **Original transaction link**: Nullable FK to original sale
3. **Store role**: Distinguish selling_store from return_store
""",
    },
    "stackable_promotions": {
        "title": "Stackable Promotions",
        "description": """
Multiple promotions can **apply to the same item**:
- Loyalty discount + coupon + sale price
- Order of application matters
- Different promo types stack differently

### Why This Breaks Models

Single promotion column is insufficient:
- Can't analyze individual promo effectiveness
- Attribution is ambiguous

### How to Handle It

1. **Bridge table**: `bridge_line_item_promotion`
2. **Application order**: Track sequence and amounts
3. **Promo type**: Distinguish exclusive vs stackable
""",
    },
}


class TrapHelpModal(ModalScreen[None]):
    """Modal showing detailed help for a specific trap."""

    CSS = """
    TrapHelpModal {
        align: center middle;
    }

    #trap-help-dialog {
        width: 70;
        height: 80%;
        padding: 1 2;
        border: round $primary;
        background: $surface;
    }

    #trap-title {
        text-align: center;
        text-style: bold;
        padding-bottom: 1;
        color: $warning;
    }

    #trap-content {
        height: 1fr;
        padding: 1;
    }

    #close-button {
        dock: bottom;
        width: 100%;
        margin-top: 1;
    }
    """

    def __init__(
        self,
        trap: EnabledTrap | None = None,
        trap_key: str | None = None,
        name: str | None = None,
    ) -> None:
        super().__init__(name=name)
        self.trap = trap
        self.trap_key = trap_key or (trap.config_source if trap else "unknown")

    def compose(self) -> ComposeResult:
        """Create the modal layout."""
        details = TRAP_DETAILS.get(self.trap_key, {})
        title = details.get("title", self.trap.name if self.trap else "Unknown Trap")
        content = details.get(
            "description",
            f"No detailed help available for this trap.\n\nTrap: {self.trap_key}"
        )

        with Vertical(id="trap-help-dialog"):
            yield Static(f"TRAP: {title}", id="trap-title")
            with VerticalScroll(id="trap-content"):
                yield Markdown(content)
            yield Button("Close", id="close-button", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle close button."""
        self.dismiss(None)

    def key_escape(self) -> None:
        """Close on escape."""
        self.dismiss(None)
