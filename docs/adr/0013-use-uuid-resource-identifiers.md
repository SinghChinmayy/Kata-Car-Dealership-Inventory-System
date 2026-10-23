# Use UUID resource identifiers

User Accounts, Vehicle Listings, Purchases, and Stock Adjustments will use server-generated UUID identifiers, stored as PostgreSQL UUID values and exposed in API paths and responses. Opaque identifiers avoid revealing record counts or permitting simple enumeration of sequential IDs.
