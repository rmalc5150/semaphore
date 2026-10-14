-- Run as the migration administrator after schema installation.
-- Roles have no application password and are not application login accounts.
CREATE ROLE IF NOT EXISTS 'tracking_reader', 'tracking_editor';
GRANT SELECT ON tracking.* TO 'tracking_reader';
GRANT SELECT ON tracking.entity_changes TO 'tracking_editor';
GRANT SELECT, INSERT, UPDATE, DELETE ON tracking.companies TO 'tracking_editor';
GRANT SELECT, INSERT, UPDATE, DELETE ON tracking.products TO 'tracking_editor';
GRANT SELECT, INSERT, UPDATE, DELETE ON tracking.product_companies TO 'tracking_editor';
GRANT SELECT, INSERT, UPDATE, DELETE ON tracking.company_aliases TO 'tracking_editor';
GRANT SELECT, INSERT, UPDATE, DELETE ON tracking.product_aliases TO 'tracking_editor';
GRANT SELECT, INSERT, UPDATE, DELETE ON tracking.company_identifiers TO 'tracking_editor';
GRANT SELECT, INSERT, UPDATE, DELETE ON tracking.product_identifiers TO 'tracking_editor';
GRANT SELECT, INSERT, UPDATE, DELETE ON tracking.company_listings TO 'tracking_editor';
GRANT SELECT, INSERT, UPDATE, DELETE ON tracking.product_contexts TO 'tracking_editor';
-- Grant one role to a separately provisioned application account and activate
-- it with SET DEFAULT ROLE. Application accounts should REQUIRE SSL.
