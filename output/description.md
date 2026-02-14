# Urban Essentials - Business Rules Documentation

This document describes the business rules and data characteristics of Urban Essentials.

## Transaction Recording

Urban Essentials maintains full line-item detail for all transactions.

Split payments are not supported; each transaction has exactly one payment. Each payment is recorded with its method and amount.

There is no void mechanism; corrections must be handled through returns.




## Time Semantics

All transactions are recorded with their business date matching the calendar date.





## Products

SKU codes are unique and never reused.

Products do not move between categories.

Some products are sold as bundles containing multiple component items. Bundle transactions may show the bundle SKU and/or its components depending on how the sale was recorded.

The product catalog includes virtual products such as gift cards and services. These items do not affect physical inventory.

### Notable Ambiguities

- Bundle sales may be recorded at the bundle level, component level, or both. The recording method is not always consistent.


## Customers

Each customer has a stable, persistent identifier.

All transactions require customer identification.




## Stores and Channels

Urban Essentials operates physical retail locations only.

Each physical store has its own identifier, registers, and staff.

Returns must be processed at the same store where the purchase was made.




## Promotions

Each line item can have at most one promotion applied.

Some promotions apply at the basket level rather than to individual line items. These discounts are based on the overall transaction (e.g., "10% off orders over $100") rather than specific products.

Promotions can be applied after a transaction has been completed. This may result in adjustment events that modify the effective price of historical transactions.

### Notable Ambiguities

- Basket-level discounts are not allocated to individual line items, making true unit economics difficult to calculate.
- Post-transaction promotions may create adjustment events that complicate revenue calculations.


## Returns

Every return includes a link to the original purchase.

Returns are processed at the current product price.



## Inventory

Inventory is not tracked in this system. There are no inventory-related events.



---

*This description is intended for data modeling purposes. It describes what the business does, not how to model it.*