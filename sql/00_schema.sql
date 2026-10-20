-- LedgerGuard database schema
-- Defining tables explicitly (instead of letting pandas guess) gives us
-- correct data types, a primary key, and a link between the two tables.

DROP TABLE IF EXISTS shipments;
DROP TABLE IF EXISTS contract_terms;

CREATE TABLE contract_terms (
    retailer              TEXT    NOT NULL,
    product               TEXT    NOT NULL,
    contract_unit_price   REAL    NOT NULL,
    max_markdown_pct      REAL    NOT NULL,
    max_chargeback_pct    REAL    NOT NULL,
    expected_return_rate  REAL    NOT NULL,
    PRIMARY KEY (retailer, product)
);

CREATE TABLE shipments (
    invoice_id            TEXT    PRIMARY KEY,
    invoice_date          TEXT    NOT NULL,   -- ISO format YYYY-MM-DD
    retailer              TEXT    NOT NULL,
    product               TEXT    NOT NULL,
    units_shipped         INTEGER NOT NULL,
    contract_unit_price   REAL    NOT NULL,
    billed_unit_price     REAL    NOT NULL,
    gross_invoice         REAL    NOT NULL,
    markdown_allowance    REAL    NOT NULL,
    chargeback            REAL    NOT NULL,
    chargeback_reason     TEXT    NOT NULL,
    units_returned        INTEGER NOT NULL,
    FOREIGN KEY (retailer, product) REFERENCES contract_terms (retailer, product)
);

-- Speeds up the date and retailer filters we will use a lot
CREATE INDEX idx_shipments_date     ON shipments (invoice_date);
CREATE INDEX idx_shipments_retailer ON shipments (retailer, product);
