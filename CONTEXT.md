# Car Dealership Inventory

This context describes the people and stock records managed by a dealership inventory system.

## People and access

**User Account**:
The registered identity used to authenticate a person, identified by a unique normalized email address and assigned one role.
_Avoid_: Profile, member, customer account

**Standard User**:
A registered person who may browse and purchase vehicles but has no inventory-management authority.
_Avoid_: Customer, regular user, buyer

**Administrator**:
A registered user authorized to manage inventory and grant administrator access to another standard user.
_Avoid_: Admin, staff user

**Account Email**:
The User Account's trimmed, lowercased email address; it is validated as an email address and unique without provider-specific rewriting.
_Avoid_: Username, login name, canonicalized email

## Inventory

**Vehicle Listing**:
A catalogued vehicle offering, defined by its shared attributes and a quantity of interchangeable units currently in stock; it is not an individual physical car.
_Avoid_: Vehicle, car, stock-keeping unit

**Stock Quantity**:
The non-negative count of purchasable units represented by a Vehicle Listing.
_Avoid_: Inventory, availability, units

**Vehicle Category**:
The controlled classification assigned to a Vehicle Listing: Sedan, SUV, Hatchback, Truck, Coupe, Convertible, or Van.
_Avoid_: Type, body style, segment

**Purchase**:
A durable record of an authenticated Standard User acquiring exactly one unit from a Vehicle Listing, including snapshots of its paid price, make, model, and category.
_Avoid_: Order, sale, transaction

**Restock**:
An Administrator's positive adjustment that adds units to a Vehicle Listing's Stock Quantity.
_Avoid_: Refill, replenish, inventory update

**Stock Adjustment**:
A durable record of an Administrator adding a specified positive quantity to a Vehicle Listing's Stock Quantity.
_Avoid_: Restock log, inventory history, adjustment entry

**Price**:
An exact decimal monetary amount for a Vehicle Listing, expressed in the system's single configured currency, INR.
_Avoid_: Cost, floating-point amount

**Deleted Vehicle Listing**:
A Vehicle Listing retired from active inventory while its historical record, remaining Stock Quantity, deletion time, and deleting Administrator remain available for auditing.
_Avoid_: Removed vehicle, erased vehicle, hard-deleted vehicle
