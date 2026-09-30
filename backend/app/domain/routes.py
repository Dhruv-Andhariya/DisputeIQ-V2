from typing import Annotated, List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, require_permission
from app.auth.permissions import Permission
from app.core.database import get_db
from app.core.errors import error_responses
from app.domain import service
from app.domain.schemas import (
    CustomerCreate, CustomerResponse, CustomerUpdate,
    DomainDisputeResponse, DisputeCreate, DisputeUpdate,
    OrderCreate, OrderResponse, OrderUpdate,
    TransactionCreate, TransactionResponse,
)
from app.users.models import User

router = APIRouter(prefix="/domain", tags=["Merchant Domain"])
DB = Annotated[Session, Depends(get_db)]
Admin = Annotated[User, Depends(require_permission(Permission.MANAGE_ORGANIZATION))]
Viewer = Annotated[User, Depends(require_permission(Permission.VIEW_CASES))]


@router.post("/customers", response_model=CustomerResponse, status_code=201, responses=error_responses(401, 403, 409))
def create_customer(data: CustomerCreate, db: DB, user: Admin):
    return service.create_customer(db, data, user.organization_id, user.id)


@router.get("/customers", response_model=List[CustomerResponse], responses=error_responses(401, 403))
def list_customers(db: DB, user: Viewer):
    return service.list_customers(db, user.organization_id)


@router.get("/customers/{customer_id}", response_model=CustomerResponse, responses=error_responses(401, 403, 404))
def get_customer(customer_id: str, db: DB, user: Viewer):
    return service.get_customer(db, customer_id, user.organization_id)


@router.patch("/customers/{customer_id}", response_model=CustomerResponse, responses=error_responses(401, 403, 404))
def update_customer(customer_id: str, data: CustomerUpdate, db: DB, user: Admin):
    return service.update_customer(db, customer_id, data, user.organization_id, user.id)


@router.post("/orders", response_model=OrderResponse, status_code=201, responses=error_responses(401, 403, 404, 409))
def create_order(data: OrderCreate, db: DB, user: Admin):
    return service.create_order(db, data, user.organization_id, user.id)


@router.get("/orders", response_model=List[OrderResponse], responses=error_responses(401, 403))
def list_orders(db: DB, user: Viewer):
    return service.list_orders(db, user.organization_id)


@router.get("/orders/{order_id}", response_model=OrderResponse, responses=error_responses(401, 403, 404))
def get_order(order_id: str, db: DB, user: Viewer):
    return service.get_order(db, order_id, user.organization_id)


@router.patch("/orders/{order_id}", response_model=OrderResponse, responses=error_responses(401, 403, 404))
def update_order(order_id: str, data: OrderUpdate, db: DB, user: Admin):
    return service.update_order(db, order_id, data, user.organization_id, user.id)


@router.post("/transactions", response_model=TransactionResponse, status_code=201, responses=error_responses(401, 403, 404, 409))
def create_transaction(data: TransactionCreate, db: DB, user: Admin):
    return service.create_transaction(db, data, user.organization_id, user.id)


@router.get("/transactions", response_model=List[TransactionResponse], responses=error_responses(401, 403))
def list_transactions(db: DB, user: Viewer):
    return service.list_transactions(db, user.organization_id)


@router.get("/transactions/{transaction_id}", response_model=TransactionResponse, responses=error_responses(401, 403, 404))
def get_transaction(transaction_id: str, db: DB, user: Viewer):
    return service.get_transaction(db, transaction_id, user.organization_id)


@router.post("/disputes", response_model=DomainDisputeResponse, status_code=201, responses=error_responses(401, 403, 404, 409))
def create_dispute(data: DisputeCreate, db: DB, user: Admin):
    return service.create_dispute(db, data, user.organization_id, user.id)


@router.get("/disputes", response_model=List[DomainDisputeResponse], responses=error_responses(401, 403))
def list_disputes(db: DB, user: Viewer):
    return service.list_disputes(db, user.organization_id)


@router.get("/disputes/{dispute_id}", response_model=DomainDisputeResponse, responses=error_responses(401, 403, 404))
def get_dispute(dispute_id: str, db: DB, user: Viewer):
    return service.get_dispute(db, dispute_id, user.organization_id)


@router.patch("/disputes/{dispute_id}", response_model=DomainDisputeResponse, responses=error_responses(401, 403, 404))
def update_dispute(dispute_id: str, data: DisputeUpdate, db: DB, user: Admin):
    return service.update_dispute(db, dispute_id, data, user.organization_id, user.id)
