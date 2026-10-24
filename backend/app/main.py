import logging
import time
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Literal, Optional
from uuid import UUID, uuid4

import jwt
from fastapi import Depends, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import PyJWTError
from pwdlib import PasswordHash
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import get_settings
from app.core.logging import configure_logging, log_event, log_failure
from app.core.request_context import request_id_from
from app.db.session import get_db_session
from app.errors import DomainError

logger = logging.getLogger("app")
# Columns that make up VehicleListingOut, in every SELECT and RETURNING clause.
LISTING_COLUMNS = "id, make, model, category, price, quantity, created_at, updated_at"
# Stock Quantity is a PostgreSQL INTEGER; restocks may not push it past this.
MAX_STOCK_QUANTITY = 2_147_483_647
MAX_INITIAL_QUANTITY = 100_000
# Deep enough for any real catalogue, small enough that OFFSET can never overflow.
MAX_PAGE = 10_000
# pg_trgm word_similarity cut-off: one wrong or missing letter in a short word still matches.
FUZZY_MATCH_THRESHOLD = 0.5
password_hasher = PasswordHash.recommended()
bearer_scheme = HTTPBearer(auto_error=False)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class UserOut(BaseModel):
    id: UUID
    email: str
    role: Literal["standard_user", "administrator"]


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"]


class VehicleCategory(str, Enum):
    sedan = "Sedan"
    suv = "SUV"
    hatchback = "Hatchback"
    truck = "Truck"
    coupe = "Coupe"
    convertible = "Convertible"
    van = "Van"


class VehicleCatalogueFields(BaseModel):
    """Descriptive listing fields shared by creation and full replacement."""

    make: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=100)
    category: VehicleCategory
    price: Decimal = Field(gt=Decimal("0"), max_digits=14, decimal_places=2)

    @field_validator("make", "model", mode="before")
    @classmethod
    def trim_text(cls, value: object) -> object:
        """Normalize catalogue text before applying its required-length rule."""
        return value.strip() if isinstance(value, str) else value


class CreateVehicleRequest(VehicleCatalogueFields):
    # A business cap that catches typos; restock may grow stock up to MAX_STOCK_QUANTITY.
    quantity: int = Field(ge=0, le=MAX_INITIAL_QUANTITY)


class UpdateVehicleRequest(VehicleCatalogueFields):
    # Stock moves only through audited purchase/restock, so quantity is an unknown field here.
    model_config = ConfigDict(extra="forbid")


class RestockRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quantity: int = Field(gt=0)


class VehicleListingOut(BaseModel):
    id: UUID
    make: str
    model: str
    category: str
    price: Decimal
    quantity: int
    created_at: datetime
    updated_at: datetime


class VehicleListingPageOut(BaseModel):
    items: list[VehicleListingOut]
    total: int
    page: int
    page_size: int


class VehicleCategoriesOut(BaseModel):
    items: list[str]


def listing_not_found() -> DomainError:
    """Missing and retired listings look the same: neither is an active resource."""
    return DomainError(404, "not_found", "The requested resource does not exist.")


def listing_is_active(session: Session, listing_id: UUID) -> bool:
    """Tell apart why a conditional stock update matched no row."""
    return (
        session.execute(
            text("SELECT 1 FROM vehicle_listings WHERE id = :id AND deleted_at IS NULL"),
            {"id": listing_id},
        ).scalar_one_or_none()
        is not None
    )


def contains_pattern(term: str) -> str:
    """Build an ILIKE substring pattern in which the user's LIKE wildcards stay literal."""
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def fetch_listing_page(
    session: Session,
    conditions: list[str],
    params: dict[str, Any],
    page: int,
    page_size: int,
    rank_first_by: str = "",
) -> VehicleListingPageOut:
    """Load one page of listings matching every condition, newest first.

    Conditions and rank_first_by are fixed SQL fragments chosen by the caller; user
    input only ever reaches the query through bound parameters. rank_first_by, when
    given, orders ahead of recency (e.g. search relevance).
    """
    effective_page_size = min(page_size, 100)
    # Retired listings stay in the table for auditing but never appear in normal reads.
    where = f"WHERE {' AND '.join(['deleted_at IS NULL', *conditions])} "
    total = session.execute(
        text(f"SELECT COUNT(*) FROM vehicle_listings {where}"), params
    ).scalar_one()
    listings = (
        session.execute(
            text(
                f"SELECT {LISTING_COLUMNS} "
                f"FROM vehicle_listings {where}ORDER BY {rank_first_by}created_at DESC, id DESC "
                "LIMIT :limit OFFSET :offset"
            ),
            {**params, "limit": effective_page_size, "offset": (page - 1) * effective_page_size},
        )
        .mappings()
        .all()
    )
    return VehicleListingPageOut(
        items=[VehicleListingOut(**listing) for listing in listings],
        total=total,
        page=page,
        page_size=effective_page_size,
    )


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),  # noqa: B008
    session: Session = Depends(get_db_session),  # noqa: B008
) -> UserOut:
    """Load the current account from the signed token subject."""
    try:
        if credentials is None:
            raise ValueError("Missing bearer token")
        claims = jwt.decode(
            credentials.credentials,
            get_settings().jwt_secret,
            algorithms=["HS256"],
        )
        user = (
            session.execute(
                text("SELECT id, email, role FROM user_accounts WHERE id = :id"),
                {"id": UUID(claims["sub"])},
            )
            .mappings()
            .one_or_none()
        )
    except (KeyError, PyJWTError, ValueError) as exc:
        raise DomainError(401, "unauthorized", "Authentication is required.") from exc
    if user is None:
        raise DomainError(401, "unauthorized", "Authentication is required.")
    request.state.user_id = str(user["id"])
    return UserOut(id=user["id"], email=user["email"], role=user["role"])


def require_admin(user: UserOut = Depends(get_current_user)) -> UserOut:  # noqa: B008
    """Require the current account to retain the Administrator role."""
    if user.role != "administrator":
        raise DomainError(403, "forbidden", "You do not have permission to perform this action.")
    return user


def validation_field_name(location: tuple[Any, ...]) -> str:
    """Name a field as clients know it, dropping FastAPI's body/query/path prefix."""
    return ".".join(str(part) for part in location if part not in ("body", "query", "path"))


def safe_validation_message(error: dict[str, Any]) -> str:
    """Field message that never repeats submitted input (docs/api-error-contract.md).

    Email-validator explanations quote the offending characters, so emails get one message.
    """
    if error["loc"] and error["loc"][-1] == "email":
        return "Enter a valid email address."
    return str(error["msg"])


def error_response(
    *,
    request: Request,
    status_code: int,
    code: str,
    message: str,
    fields: Optional[dict[str, str]] = None,
) -> JSONResponse:
    error: dict[str, Any] = {
        "code": code,
        "message": message,
        "request_id": request_id_from(request) or str(uuid4()),
    }
    if fields:
        error["fields"] = fields
    return JSONResponse(status_code=status_code, content={"error": error})


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    app = FastAPI(title="Car Dealership Inventory API", version="0.1.0")

    @app.middleware("http")
    async def add_request_context(request: Request, call_next: Any) -> Any:
        incoming = request.headers.get("X-Request-ID")
        try:
            request_id = str(UUID(incoming)) if incoming else str(uuid4())
        except ValueError:
            request_id = str(uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        # Crashes are answered here, inside CORS, so even a 500 is traceable and readable.
        try:
            response = await call_next(request)
        except Exception as exc:
            log_failure(
                logger, "request.failed", exc, request_id=request_id, error=type(exc).__name__
            )
            response = error_response(
                request=request,
                status_code=500,
                code="internal_error",
                message="An unexpected error occurred.",
            )
        response.headers["X-Request-ID"] = request_id
        log_event(
            logger,
            "request.completed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
            user_id=getattr(request.state, "user_id", None),
        )
        return response

    # Added after the request-context middleware so CORS wraps it and decorates its 500s.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        return error_response(
            request=request,
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            fields=exc.fields,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        fields = {
            validation_field_name(error["loc"]): safe_validation_message(error)
            for error in exc.errors()
        }
        return error_response(
            request=request,
            status_code=422,
            code="validation_error",
            message="Request validation failed.",
            fields=fields,
        )

    # Starlette's base class also covers routing 404/405s that never reach a FastAPI route.
    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        status_codes = {
            401: ("unauthorized", "Authentication is required."),
            403: ("forbidden", "You do not have permission to perform this action."),
            404: ("not_found", "The requested resource does not exist."),
            405: ("method_not_allowed", "The request method is not allowed."),
        }
        code, message = status_codes.get(exc.status_code, ("http_error", "The request failed."))
        return error_response(
            request=request, status_code=exc.status_code, code=code, message=message
        )

    @app.get("/health", tags=["operations"])
    def health_check(session: Session = Depends(get_db_session)) -> dict[str, str]:  # noqa: B008
        try:
            session.execute(text("SELECT 1"))
        except SQLAlchemyError as exc:
            raise DomainError(503, "service_unavailable", "Database is unavailable.") from exc
        return {"status": "ok"}

    @app.get("/api/auth/me", response_model=UserOut, tags=["auth"])
    def current_user(user: UserOut = Depends(get_current_user)) -> UserOut:  # noqa: B008
        return user

    @app.post("/api/auth/register", status_code=201, response_model=UserOut, tags=["auth"])
    def register(
        payload: RegisterRequest,
        session: Session = Depends(get_db_session),  # noqa: B008
    ) -> UserOut:
        user_id = uuid4()
        email = payload.email.strip().lower()
        role = "standard_user"
        try:
            session.execute(
                text(
                    "INSERT INTO user_accounts (id, email, password_hash, role) "
                    "VALUES (:id, :email, :password_hash, :role)"
                ),
                {
                    "id": user_id,
                    "email": email,
                    "password_hash": password_hasher.hash(payload.password),
                    "role": role,
                },
            )
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise DomainError(
                409,
                "duplicate_email",
                "An account with this email already exists.",
            ) from exc
        return UserOut(id=user_id, email=email, role=role)

    @app.post("/api/auth/login", response_model=TokenResponse, tags=["auth"])
    def login(
        payload: LoginRequest,
        session: Session = Depends(get_db_session),  # noqa: B008
    ) -> TokenResponse:
        user = (
            session.execute(
                text("SELECT id, password_hash FROM user_accounts WHERE email = :email"),
                {"email": payload.email.strip().lower()},
            )
            .mappings()
            .one_or_none()
        )
        if user is None or not password_hasher.verify(payload.password, user["password_hash"]):
            raise DomainError(401, "invalid_credentials", "Email or password is incorrect.")

        issued_at = int(time.time())
        access_token = jwt.encode(
            {
                "sub": str(user["id"]),
                "iat": issued_at,
                "exp": issued_at + get_settings().jwt_access_token_minutes * 60,
            },
            get_settings().jwt_secret,
            algorithm="HS256",
        )
        return TokenResponse(access_token=access_token, token_type="bearer")

    @app.post("/api/vehicles", status_code=201, response_model=VehicleListingOut, tags=["vehicles"])
    def create_vehicle_listing(
        payload: CreateVehicleRequest,
        _: UserOut = Depends(require_admin),  # noqa: B008
        session: Session = Depends(get_db_session),  # noqa: B008
    ) -> VehicleListingOut:
        """Add a listing to the active inventory catalogue."""
        listing = (
            session.execute(
                text(
                    "INSERT INTO vehicle_listings (id, make, model, category, price, quantity) "
                    "VALUES (:id, :make, :model, :category, :price, :quantity) "
                    f"RETURNING {LISTING_COLUMNS}"
                ),
                {
                    "id": uuid4(),
                    "make": payload.make,
                    "model": payload.model,
                    "category": payload.category.value,
                    "price": payload.price,
                    "quantity": payload.quantity,
                },
            )
            .mappings()
            .one()
        )
        session.commit()
        return VehicleListingOut(**listing)

    @app.get("/api/vehicles", response_model=VehicleListingPageOut, tags=["vehicles"])
    def list_vehicle_listings(
        _: UserOut = Depends(get_current_user),  # noqa: B008
        session: Session = Depends(get_db_session),  # noqa: B008
        page: int = Query(default=1, ge=1, le=MAX_PAGE),
        page_size: int = Query(default=20, ge=1),
    ) -> VehicleListingPageOut:
        """Return active catalogue listings in stable newest-first order."""
        return fetch_listing_page(session, [], {}, page, page_size)

    @app.get("/api/vehicles/search", response_model=VehicleListingPageOut, tags=["vehicles"])
    def search_vehicle_listings(
        _: UserOut = Depends(get_current_user),  # noqa: B008
        session: Session = Depends(get_db_session),  # noqa: B008
        q: Optional[str] = Query(default=None, max_length=100),
        make: Optional[str] = None,
        model: Optional[str] = None,
        category: Optional[VehicleCategory] = None,
        min_price: Optional[Decimal] = Query(  # noqa: B008
            default=None, ge=0, max_digits=14, decimal_places=2
        ),
        max_price: Optional[Decimal] = Query(  # noqa: B008
            default=None, ge=0, max_digits=14, decimal_places=2
        ),
        page: int = Query(default=1, ge=1, le=MAX_PAGE),
        page_size: int = Query(default=20, ge=1),
    ) -> VehicleListingPageOut:
        """Return active listings matching every supplied filter, newest first."""
        if min_price is not None and max_price is not None and min_price > max_price:
            raise DomainError(
                422,
                "validation_error",
                "Request validation failed.",
                {"min_price": "Must be less than or equal to max_price."},
            )
        conditions: list[str] = []
        params: dict[str, Any] = {}
        # Blank form fields arrive as empty or whitespace-only terms; they mean "no filter".
        q = q.strip() if q else None
        make = make.strip() if make else None
        model = model.strip() if model else None
        if q:
            # The SPA's single box: every word must appear in "make model", either as a
            # substring or as a close trigram match, so small typos ("hilx") still find it.
            for index, word in enumerate(q.split()):
                conditions.append(
                    f"((make || ' ' || model) ILIKE :q{index} ESCAPE '\\' "
                    f"OR word_similarity(:w{index}, make || ' ' || model) >= :fuzzy)"
                )
                params[f"q{index}"] = contains_pattern(word)
                params[f"w{index}"] = word.lower()
            params["fuzzy"] = FUZZY_MATCH_THRESHOLD
        if make:
            conditions.append("make ILIKE :make ESCAPE '\\'")
            params["make"] = contains_pattern(make)
        if model:
            conditions.append("model ILIKE :model ESCAPE '\\'")
            params["model"] = contains_pattern(model)
        if category is not None:
            conditions.append("category = :category")
            params["category"] = category.value
        if min_price is not None:
            conditions.append("price >= :min_price")
            params["min_price"] = min_price
        if max_price is not None:
            conditions.append("price <= :max_price")
            params["max_price"] = max_price
        rank = ""
        if q:
            # Closest overall match to everything typed first; recency breaks ties.
            rank = "word_similarity(:whole_q, make || ' ' || model) DESC, "
            params["whole_q"] = q.lower()
        return fetch_listing_page(session, conditions, params, page, page_size, rank)

    @app.get("/api/vehicles/categories", response_model=VehicleCategoriesOut, tags=["vehicles"])
    def list_vehicle_categories(
        _: UserOut = Depends(get_current_user),  # noqa: B008
    ) -> VehicleCategoriesOut:
        """Expose the backend-owned category vocabulary to authenticated clients."""
        return VehicleCategoriesOut(items=[category.value for category in VehicleCategory])

    @app.put("/api/vehicles/{listing_id}", response_model=VehicleListingOut, tags=["vehicles"])
    def update_vehicle_listing(
        listing_id: UUID,
        payload: UpdateVehicleRequest,
        _: UserOut = Depends(require_admin),  # noqa: B008
        session: Session = Depends(get_db_session),  # noqa: B008
    ) -> VehicleListingOut:
        """Replace a listing's catalogue fields; stock changes only via purchase or restock."""
        listing = (
            session.execute(
                text(
                    "UPDATE vehicle_listings SET make = :make, model = :model, "
                    "category = :category, price = :price, updated_at = CURRENT_TIMESTAMP "
                    "WHERE id = :id AND deleted_at IS NULL "
                    f"RETURNING {LISTING_COLUMNS}"
                ),
                {
                    "id": listing_id,
                    "make": payload.make,
                    "model": payload.model,
                    "category": payload.category.value,
                    "price": payload.price,
                },
            )
            .mappings()
            .one_or_none()
        )
        if listing is None:
            raise listing_not_found()
        session.commit()
        return VehicleListingOut(**listing)

    @app.delete("/api/vehicles/{listing_id}", status_code=204, tags=["vehicles"])
    def delete_vehicle_listing(
        listing_id: UUID,
        admin: UserOut = Depends(require_admin),  # noqa: B008
        session: Session = Depends(get_db_session),  # noqa: B008
    ) -> Response:
        """Retire a listing from active inventory while keeping it for auditing."""
        deleted = session.execute(
            text(
                "UPDATE vehicle_listings "
                "SET deleted_at = CURRENT_TIMESTAMP, deleted_by = :deleted_by "
                "WHERE id = :id AND deleted_at IS NULL RETURNING id"
            ),
            {"id": listing_id, "deleted_by": admin.id},
        ).one_or_none()
        if deleted is None:
            raise listing_not_found()
        session.commit()
        return Response(status_code=204)

    @app.post(
        "/api/vehicles/{listing_id}/purchase", response_model=VehicleListingOut, tags=["inventory"]
    )
    def purchase_vehicle_listing(
        listing_id: UUID,
        purchaser: UserOut = Depends(get_current_user),  # noqa: B008
        session: Session = Depends(get_db_session),  # noqa: B008
    ) -> VehicleListingOut:
        """Buy one unit of a listing and record the sale with catalogue snapshots."""
        # One conditional statement: the row lock serializes concurrent buyers, and each
        # re-checks quantity > 0 after the previous one commits, so stock can't oversell.
        listing = (
            session.execute(
                text(
                    "UPDATE vehicle_listings SET quantity = quantity - 1 "
                    "WHERE id = :id AND quantity > 0 AND deleted_at IS NULL "
                    f"RETURNING {LISTING_COLUMNS}"
                ),
                {"id": listing_id},
            )
            .mappings()
            .one_or_none()
        )
        if listing is None:
            if not listing_is_active(session, listing_id):
                raise listing_not_found()
            raise DomainError(409, "out_of_stock", "This vehicle is out of stock.")
        # Same transaction as the decrement: either both persist or neither does.
        session.execute(
            text(
                "INSERT INTO purchases "
                "(id, listing_id, purchaser_id, price, make, model, category) "
                "VALUES (:id, :listing_id, :purchaser_id, :price, :make, :model, :category)"
            ),
            {
                "id": uuid4(),
                "listing_id": listing["id"],
                "purchaser_id": purchaser.id,
                "price": listing["price"],
                "make": listing["make"],
                "model": listing["model"],
                "category": listing["category"],
            },
        )
        session.commit()
        return VehicleListingOut(**listing)

    @app.post(
        "/api/vehicles/{listing_id}/restock", response_model=VehicleListingOut, tags=["inventory"]
    )
    def restock_vehicle_listing(
        listing_id: UUID,
        payload: RestockRequest,
        admin: UserOut = Depends(require_admin),  # noqa: B008
        session: Session = Depends(get_db_session),  # noqa: B008
    ) -> VehicleListingOut:
        """Add units to a listing's stock and record who added how many."""
        # Relative increment, so a concurrent purchase or restock is never overwritten.
        listing = (
            session.execute(
                text(
                    "UPDATE vehicle_listings SET quantity = quantity + :quantity "
                    "WHERE id = :id AND deleted_at IS NULL "
                    "AND quantity <= :max_stock - :quantity "
                    f"RETURNING {LISTING_COLUMNS}"
                ),
                {"id": listing_id, "quantity": payload.quantity, "max_stock": MAX_STOCK_QUANTITY},
            )
            .mappings()
            .one_or_none()
        )
        if listing is None:
            if not listing_is_active(session, listing_id):
                raise listing_not_found()
            raise DomainError(
                422,
                "validation_error",
                "Request validation failed.",
                {"quantity": "Would exceed the maximum stock quantity."},
            )
        # Same transaction as the increment: stock never rises without an audit record.
        session.execute(
            text(
                "INSERT INTO stock_adjustments (id, listing_id, administrator_id, quantity) "
                "VALUES (:id, :listing_id, :administrator_id, :quantity)"
            ),
            {
                "id": uuid4(),
                "listing_id": listing["id"],
                "administrator_id": admin.id,
                "quantity": payload.quantity,
            },
        )
        session.commit()
        return VehicleListingOut(**listing)

    return app


app = create_app()
