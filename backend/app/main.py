import logging
import time
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Literal, Optional
from uuid import UUID, uuid4

import jwt
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import PyJWTError
from pwdlib import PasswordHash
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import configure_logging, log_event
from app.core.request_context import request_id_from
from app.db.session import get_db_session
from app.errors import DomainError

logger = logging.getLogger("app")
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
    quantity: int = Field(ge=0)


class UpdateVehicleRequest(VehicleCatalogueFields):
    # Stock moves only through audited purchase/restock, so quantity is an unknown field here.
    model_config = ConfigDict(extra="forbid")


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
) -> VehicleListingPageOut:
    """Load one newest-first page of listings matching every condition.

    Conditions are fixed SQL fragments chosen by the caller; user input only
    ever reaches the query through bound parameters.
    """
    effective_page_size = min(page_size, 100)
    where = f"WHERE {' AND '.join(conditions)} " if conditions else ""
    total = session.execute(
        text(f"SELECT COUNT(*) FROM vehicle_listings {where}"), params
    ).scalar_one()
    listings = (
        session.execute(
            text(
                "SELECT id, make, model, category, price, quantity, created_at, updated_at "
                f"FROM vehicle_listings {where}ORDER BY created_at DESC, id DESC "
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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    @app.middleware("http")
    async def add_request_context(request: Request, call_next: Any) -> Any:
        incoming = request.headers.get("X-Request-ID")
        try:
            request_id = str(UUID(incoming)) if incoming else str(uuid4())
        except ValueError:
            request_id = str(uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
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
        # Clients name fields, not request locations, so drop the body/query/path prefix.
        request_locations = ("body", "query", "path")
        fields = {
            ".".join(str(part) for part in error["loc"] if part not in request_locations): error[
                "msg"
            ]
            for error in exc.errors()
        }
        return error_response(
            request=request,
            status_code=422,
            code="validation_error",
            message="Request validation failed.",
            fields=fields,
        )

    @app.exception_handler(HTTPException)
    async def handle_http_error(request: Request, exc: HTTPException) -> JSONResponse:
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

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        log_event(
            logger, "request.failed", request_id=request_id_from(request), error=type(exc).__name__
        )
        return error_response(
            request=request,
            status_code=500,
            code="internal_error",
            message="An unexpected error occurred.",
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

    @app.get("/api/auth/admin-check", tags=["auth"])
    def administrator_check(_: UserOut = Depends(require_admin)) -> dict[str, str]:  # noqa: B008
        return {"status": "ok"}

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
                    "RETURNING id, make, model, category, price, quantity, created_at, updated_at"
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
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1),
    ) -> VehicleListingPageOut:
        """Return active catalogue listings in stable newest-first order."""
        return fetch_listing_page(session, [], {}, page, page_size)

    @app.get("/api/vehicles/search", response_model=VehicleListingPageOut, tags=["vehicles"])
    def search_vehicle_listings(
        _: UserOut = Depends(get_current_user),  # noqa: B008
        session: Session = Depends(get_db_session),  # noqa: B008
        make: Optional[str] = None,
        model: Optional[str] = None,
        category: Optional[VehicleCategory] = None,
        min_price: Optional[Decimal] = Query(  # noqa: B008
            default=None, ge=0, max_digits=14, decimal_places=2
        ),
        max_price: Optional[Decimal] = Query(  # noqa: B008
            default=None, ge=0, max_digits=14, decimal_places=2
        ),
        page: int = Query(default=1, ge=1),
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
        make = make.strip() if make else None
        model = model.strip() if model else None
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
        return fetch_listing_page(session, conditions, params, page, page_size)

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
                    "WHERE id = :id "
                    "RETURNING id, make, model, category, price, quantity, created_at, updated_at"
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
            raise DomainError(404, "not_found", "The requested resource does not exist.")
        session.commit()
        return VehicleListingOut(**listing)

    return app


app = create_app()
