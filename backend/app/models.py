import uuid
from datetime import datetime, date

from pydantic import EmailStr
from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy import String
from sqlalchemy.types import TypeDecorator



# Custom UUID type that works with both SQLite and PostgreSQL
class UUIDString(TypeDecorator):
    """
    Store UUID as string in SQLite, native UUID in PostgreSQL.
    Handles type conversion automatically based on database dialect.
    """
    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        """Use native UUID for PostgreSQL, String for SQLite"""
        if dialect.name == 'postgresql':
            from sqlalchemy.dialects.postgresql import UUID
            return dialect.type_descriptor(UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        """Convert to appropriate type for database"""
        if value is None:
            return value
        if dialect.name == 'postgresql':
            # PostgreSQL handles UUID natively
            if isinstance(value, str):
                return uuid.UUID(value)
            return value
        else:
            # SQLite stores as string
            if isinstance(value, uuid.UUID):
                return str(value)
            return value

    def process_result_value(self, value, dialect):
        """Convert from database type to Python UUID"""
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        if isinstance(value, str):
            return uuid.UUID(value)
        return value



# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, sa_type=UUIDString(36))
    hashed_password: str
    items: list["Item"] = Relationship(back_populates="owner", cascade_delete=True)


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# ============================================================================
# ATTENDEE MODELS (Customer Authentication)
# ============================================================================

# Shared properties for attendees
class AttendeeBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    first_name: str | None = Field(default=None, max_length=255)
    last_name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    birthdate: date | None = None
    country: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)


# Properties to receive via API on signup
class AttendeeSignup(SQLModel):
    """Schema matching Figma signup form"""
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    first_name: str = Field(min_length=1, max_length=255)
    last_name: str = Field(min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    birthdate: date | None = None
    country: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)


# Properties to receive via API on signin
class AttendeeSignin(SQLModel):
    """Schema matching Figma signin form"""
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)


# Database model for attendees
class Attendee(AttendeeBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, sa_type=UUIDString(36))
    shopify_customer_id: int | None = Field(default=None, unique=True, index=True)
    google_id: str | None = Field(default=None, unique=True, index=True, max_length=255)
    hashed_password: str | None = None  # Optional for OAuth users
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    orders: list["Order"] = Relationship(back_populates="attendee", cascade_delete=True)

    @property
    def full_name(self) -> str:
        """Computed property for full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name or ""



# Properties to return via API
class AttendeePublic(AttendeeBase):
    id: uuid.UUID
    created_at: datetime
    
    @property
    def full_name(self) -> str:
        """Computed property for full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name or ""


# Order models
class OrderBase(SQLModel):
    shopify_order_id: int | None = Field(default=None, unique=True, index=True)
    order_number: str | None = Field(default=None, max_length=50)
    total_price: float
    currency: str = Field(default="USD", max_length=3)
    status: str = Field(max_length=50)


class Order(OrderBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, sa_type=UUIDString(36))
    attendee_id: uuid.UUID = Field(foreign_key="attendee.id", ondelete="CASCADE", sa_type=UUIDString(36))
    attendee: Attendee | None = Relationship(back_populates="orders")
    items: list["OrderItem"] = Relationship(back_populates="order", cascade_delete=True)
    created_at: datetime
    updated_at: datetime


class OrderPublic(OrderBase):
    id: uuid.UUID
    attendee_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# Order item models (tickets)
class OrderItemBase(SQLModel):
    shopify_variant_id: int
    ticket_name: str = Field(max_length=255)
    quantity: int
    price: float
    event_id: int | None = None
    qr_code: str | None = None
    checked_in: bool = False
    checked_in_at: datetime | None = None


class OrderItem(OrderItemBase, table=True):
    __tablename__ = "order_item"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, sa_type=UUIDString(36))
    order_id: uuid.UUID = Field(foreign_key="order.id", ondelete="CASCADE", sa_type=UUIDString(36))
    order: Order | None = Relationship(back_populates="items")


class OrderItemPublic(OrderItemBase):
    id: uuid.UUID
    order_id: uuid.UUID


# Processed webhooks for idempotency
class ProcessedWebhook(SQLModel, table=True):
    __tablename__ = "processed_webhook"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, sa_type=UUIDString(36))
    webhook_id: str = Field(unique=True, index=True, max_length=255)
    topic: str = Field(max_length=100)
    processed_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# ITEM MODELS (Original)
# ============================================================================

# Shared properties
class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Properties to receive on item creation
class ItemCreate(ItemBase):
    pass


# Properties to receive on item update
class ItemUpdate(ItemBase):
    title: str | None = Field(default=None, min_length=1, max_length=255)  # type: ignore


# Database model, database table inferred from class name
class Item(ItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, sa_type=UUIDString(36))
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE", sa_type=UUIDString(36)
    )
    owner: User | None = Relationship(back_populates="items")


# Properties to return via API, id is always required
class ItemPublic(ItemBase):
    id: uuid.UUID
    owner_id: uuid.UUID


class ItemsPublic(SQLModel):
    data: list[ItemPublic]
    count: int


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)

