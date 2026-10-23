# Control vehicle categories in the backend

Vehicle Category will be one backend-owned enumeration—Sedan, SUV, Hatchback, Truck, Coupe, Convertible, and Van—stored as a PostgreSQL `VARCHAR` protected by a `CHECK` constraint. Create, update, and search requests with a value outside that vocabulary return 422, and a public category endpoint exposes the same list so the frontend does not duplicate it.
