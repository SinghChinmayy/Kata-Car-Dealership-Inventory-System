# Use synchronous SQLAlchemy 2 and Alembic

The API will use SQLAlchemy 2 with synchronous sessions for relational persistence, and Alembic for versioned PostgreSQL schema migrations. The kata does not require the additional operational and testing complexity of async database access; the synchronous model keeps transaction handling direct while Alembic provides a reproducible schema history.

## Considered Options

SQLAlchemy async sessions, Django ORM, and Prisma.
