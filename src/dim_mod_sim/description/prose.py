"""Natural language variations for shop descriptions."""

from dim_mod_sim.core.random import SeededRandom


class ProseVariations:
    """Provides natural language variations for descriptions."""

    TRANSACTION_GRAIN_PHRASES = {
        "receipt_level": [
            "records transactions at the receipt level, with line items aggregated into a single total",
            "captures only receipt-level totals without itemized breakdowns",
            "stores transactions as whole receipts rather than individual line items",
        ],
        "line_item_level": [
            "tracks every individual line item within each transaction",
            "records each product sold as a separate line item",
            "maintains full line-item detail for all transactions",
        ],
        "mixed": [
            "uses a mixed approach where some transactions have line-item detail while others are receipt-level only",
            "inconsistently records transactions—some with full detail, others aggregated",
            "employs varying levels of transaction detail depending on the source",
        ],
    }

    MULTIPLE_PAYMENTS_PHRASES = {
        True: [
            "Customers may split payment across multiple methods within a single transaction",
            "A single transaction can include multiple payment types",
            "Split-tender transactions are supported, allowing customers to use multiple payment methods",
        ],
        False: [
            "Each transaction uses a single payment method",
            "Transactions are settled with one payment type only",
            "Split payments are not supported; each transaction has exactly one payment",
        ],
    }

    VOIDS_PHRASES = {
        True: [
            "Transactions can be voided after completion",
            "Completed transactions may be cancelled via a void operation",
            "Void events can cancel entire transactions after they have been recorded",
        ],
        False: [
            "Once completed, transactions cannot be voided",
            "There is no void mechanism; corrections must be handled through returns",
            "Transaction voids are not supported",
        ],
    }

    TIMESTAMP_RELATION_PHRASES = {
        "same": [
            "The transaction timestamp and business date always match",
            "All transactions are recorded with their business date matching the calendar date",
            "There is no distinction between transaction timestamp and business date",
        ],
        "different": [
            "The transaction timestamp may differ from the business date",
            "Late-night transactions may be recorded with the previous day's business date",
            "Business dates can diverge from actual timestamps, particularly around day boundaries",
        ],
    }

    LATE_ARRIVING_PHRASES = {
        True: [
            "Events may arrive out of order relative to their actual occurrence",
            "Late-arriving events are permitted; the system may receive events after their timestamp would suggest",
            "Event ordering is not guaranteed to match chronological order",
        ],
        False: [
            "Events arrive in chronological order",
            "Late-arriving events are not a concern in this system",
            "Events are processed in timestamp order without delays",
        ],
    }

    BACKDATED_CORRECTIONS_PHRASES = {
        True: [
            "Corrections can be applied retroactively with backdated effective dates",
            "Historical transactions may be corrected with the correction taking effect on a past date",
            "Backdated corrections are supported, meaning a correction recorded today might be effective as of last week",
        ],
        False: [
            "Corrections, if any, take effect only as of the current date",
            "There is no mechanism for backdating corrections",
            "All changes are applied going forward without historical restatement",
        ],
    }

    SKU_REUSE_PHRASES = {
        True: [
            "SKU codes may be reused over time for different products",
            "A given SKU may refer to different products at different points in time",
            "SKUs are not permanently assigned; they can be recycled when products are discontinued",
        ],
        False: [
            "SKU codes are unique and never reused",
            "Once assigned, a SKU permanently identifies one specific product",
            "SKUs are immutable identifiers that never change meaning",
        ],
    }

    HIERARCHY_CHANGE_PHRASES = {
        "none": [
            "Product hierarchies remain fixed and never change",
            "Category assignments are permanent",
            "Products do not move between categories",
        ],
        "occasional": [
            "Product hierarchies may occasionally change",
            "Products are sometimes reclassified to different categories",
            "Category assignments can change, though this happens infrequently",
        ],
        "frequent": [
            "Product hierarchies change frequently",
            "Products are often reclassified between categories",
            "Category assignments are fluid and change regularly",
        ],
    }

    CUSTOMER_RELIABILITY_PHRASES = {
        "reliable": [
            "Customer IDs consistently identify the same person across transactions",
            "The customer identification system is reliable and accurate",
            "Each customer has a stable, persistent identifier",
        ],
        "unreliable": [
            "Customer IDs may not consistently identify the same person",
            "The same customer might have multiple IDs, or different customers might share an ID",
            "Customer identification is inconsistent and should be treated with caution",
        ],
        "absent": [
            "Customer identification is not tracked",
            "Transactions do not include customer information",
            "There is no customer ID in the system",
        ],
    }

    RETURNS_REFERENCE_PHRASES = {
        "always": [
            "Returns always reference the original sale transaction",
            "Every return includes a link to the original purchase",
            "Return records contain a mandatory reference to the originating sale",
        ],
        "sometimes": [
            "Returns sometimes reference the original sale, but not always",
            "The original transaction reference is present in some return records but absent in others",
            "Return-to-sale linkage is inconsistent; some returns can be traced, others cannot",
        ],
        "never": [
            "Returns do not reference the original sale",
            "There is no link between return events and the original purchase",
            "Returns are recorded independently without connection to prior sales",
        ],
    }

    RETURNS_PRICING_PHRASES = {
        "original_price": [
            "Returns are processed at the original purchase price",
            "The refund amount matches what the customer originally paid",
            "Return pricing uses the price from the original transaction",
        ],
        "current_price": [
            "Returns are processed at the current product price",
            "Refunds are calculated based on the item's current price, not the purchase price",
            "Return pricing uses today's price regardless of what was originally paid",
        ],
        "arbitrary_override": [
            "Return pricing can be arbitrarily overridden",
            "The refund amount may differ from both the original and current price at manager discretion",
            "Return prices are not constrained to match any particular reference price",
        ],
    }

    INVENTORY_TYPE_PHRASES = {
        "transactional": [
            "Inventory is tracked through individual adjustment events",
            "Each inventory change generates a separate event",
            "Inventory movements are recorded as discrete transactions",
        ],
        "periodic_snapshot": [
            "Inventory is captured through periodic snapshots",
            "Inventory levels are recorded at fixed intervals rather than per-transaction",
            "The system captures point-in-time inventory counts rather than individual movements",
        ],
        "both": [
            "Inventory is tracked both transactionally and through periodic snapshots",
            "The system records individual inventory adjustments and also takes regular snapshots",
            "Inventory data includes both granular movement events and periodic count records",
        ],
    }

    def __init__(self, rng: SeededRandom) -> None:
        self.rng = rng

    def get_phrase(self, category: str, key: str) -> str:
        """Get a deterministically selected phrase variation."""
        phrases_dict = getattr(self, f"{category.upper()}_PHRASES", {})
        phrases = phrases_dict.get(key, [f"{category}: {key}"])
        return self.rng.choice(phrases)
