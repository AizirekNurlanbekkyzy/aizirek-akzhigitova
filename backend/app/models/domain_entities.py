from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.domain import (
    AssignmentStatus,
    EstimateStatus,
    MaintenanceFrequency,
    SlaStatus,
)
from app.models.entities import Base


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("organization_id", "user_id"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(32))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class Property(Base):
    __tablename__ = "properties"
    __table_args__ = (UniqueConstraint("organization_id", "code"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    code: Mapped[str] = mapped_column(String(64))
    address: Mapped[str] = mapped_column(String(500))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("organization_id", "name"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Skill(Base):
    __tablename__ = "skills"
    __table_args__ = (UniqueConstraint("organization_id", "name"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))


class Technician(Base):
    __tablename__ = "technicians"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class TechnicianSkill(Base):
    __tablename__ = "technician_skills"
    __table_args__ = (UniqueConstraint("technician_id", "skill_id"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    technician_id: Mapped[UUID] = mapped_column(ForeignKey("technicians.id"), index=True)
    skill_id: Mapped[UUID] = mapped_column(ForeignKey("skills.id"), index=True)


class SkillCategory(Base):
    __tablename__ = "skill_categories"
    __table_args__ = (UniqueConstraint("category_id", "skill_id"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    category_id: Mapped[UUID] = mapped_column(ForeignKey("categories.id"), index=True)
    skill_id: Mapped[UUID] = mapped_column(ForeignKey("skills.id"), index=True)


class TechnicianWorkingHour(Base):
    __tablename__ = "technician_working_hours"
    __table_args__ = (UniqueConstraint("technician_id", "weekday"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    technician_id: Mapped[UUID] = mapped_column(ForeignKey("technicians.id"), index=True)
    weekday: Mapped[int] = mapped_column(Integer)
    start_minute: Mapped[int] = mapped_column(Integer)
    end_minute: Mapped[int] = mapped_column(Integer)


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (UniqueConstraint("organization_id", "asset_tag"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    property_id: Mapped[UUID] = mapped_column(ForeignKey("properties.id"), index=True)
    category_id: Mapped[UUID | None] = mapped_column(ForeignKey("categories.id"))
    asset_tag: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(160))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Assignment(Base):
    __tablename__ = "assignments"
    __table_args__ = (
        CheckConstraint("ends_at > starts_at", name="ck_assignment_positive_duration"),
        Index(
            "ix_assignment_tenant_technician_time", "organization_id", "technician_id", "starts_at"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    request_id: Mapped[UUID] = mapped_column(ForeignKey("service_requests.id"), index=True)
    technician_id: Mapped[UUID] = mapped_column(ForeignKey("technicians.id"), index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[AssignmentStatus] = mapped_column(
        Enum(AssignmentStatus, native_enum=False, length=24), default=AssignmentStatus.OFFERED
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class AssignmentEvent(Base):
    __tablename__ = "assignment_events"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    assignment_id: Mapped[UUID] = mapped_column(ForeignKey("assignments.id"), index=True)
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    from_status: Mapped[str | None] = mapped_column(String(24))
    to_status: Mapped[str] = mapped_column(String(24))
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class Estimate(Base):
    __tablename__ = "estimates"
    __table_args__ = (UniqueConstraint("request_id", "version"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    request_id: Mapped[UUID] = mapped_column(ForeignKey("service_requests.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    previous_version_id: Mapped[UUID | None] = mapped_column(ForeignKey("estimates.id"))
    status: Mapped[EstimateStatus] = mapped_column(
        Enum(EstimateStatus, native_enum=False, length=32), default=EstimateStatus.DRAFT
    )
    total_tyiyn: Mapped[int] = mapped_column(Integer, default=0)
    comment: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EstimateLine(Base):
    __tablename__ = "estimate_lines"
    __table_args__ = (CheckConstraint("quantity > 0", name="ck_estimate_line_positive_quantity"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    estimate_id: Mapped[UUID] = mapped_column(ForeignKey("estimates.id"), index=True)
    kind: Mapped[str] = mapped_column(String(16))
    description: Mapped[str] = mapped_column(String(500))
    inventory_item_id: Mapped[UUID | None] = mapped_column(ForeignKey("inventory_items.id"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    unit_price_tyiyn: Mapped[int] = mapped_column(Integer)


class EstimateEvent(Base):
    __tablename__ = "estimate_events"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    estimate_id: Mapped[UUID] = mapped_column(ForeignKey("estimates.id"), index=True)
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    from_status: Mapped[str | None] = mapped_column(String(32))
    to_status: Mapped[str] = mapped_column(String(32))
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class InventoryItem(Base):
    __tablename__ = "inventory_items"
    __table_args__ = (
        UniqueConstraint("organization_id", "sku"),
        CheckConstraint("quantity_on_hand >= 0", name="ck_inventory_nonnegative"),
        CheckConstraint("minimum_quantity >= 0", name="ck_inventory_minimum_nonnegative"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    sku: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(160))
    unit: Mapped[str] = mapped_column(String(24))
    quantity_on_hand: Mapped[int] = mapped_column(Integer, default=0)
    minimum_quantity: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class StockMovement(Base):
    __tablename__ = "stock_movements"
    __table_args__ = (
        UniqueConstraint("organization_id", "idempotency_key"),
        CheckConstraint("quantity_delta <> 0", name="ck_stock_movement_nonzero"),
        Index("ix_stock_movement_item_time", "organization_id", "item_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    item_id: Mapped[UUID] = mapped_column(ForeignKey("inventory_items.id"), index=True)
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    quantity_delta: Mapped[int] = mapped_column(Integer)
    resulting_quantity: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(300))
    idempotency_key: Mapped[str] = mapped_column(String(128))
    payload_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class MaterialUsage(Base):
    __tablename__ = "material_usage"
    __table_args__ = (UniqueConstraint("organization_id", "idempotency_key"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    request_id: Mapped[UUID] = mapped_column(ForeignKey("service_requests.id"), index=True)
    item_id: Mapped[UUID] = mapped_column(ForeignKey("inventory_items.id"), index=True)
    technician_id: Mapped[UUID] = mapped_column(ForeignKey("technicians.id"))
    quantity: Mapped[int] = mapped_column(Integer)
    idempotency_key: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class SlaClock(Base):
    __tablename__ = "sla_clocks"
    __table_args__ = (
        UniqueConstraint("request_id"),
        CheckConstraint("initial_budget_seconds > 0", name="ck_sla_positive_budget"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    request_id: Mapped[UUID] = mapped_column(ForeignKey("service_requests.id"), index=True)
    initial_budget_seconds: Mapped[int] = mapped_column(Integer)
    remaining_seconds: Mapped[int] = mapped_column(Integer)
    status: Mapped[SlaStatus] = mapped_column(Enum(SlaStatus, native_enum=False, length=16))
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class SlaEvent(Base):
    __tablename__ = "sla_events"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    request_id: Mapped[UUID] = mapped_column(ForeignKey("service_requests.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(32))
    remaining_seconds: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class MaintenancePlan(Base):
    __tablename__ = "maintenance_plans"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    asset_id: Mapped[UUID] = mapped_column(ForeignKey("assets.id"), index=True)
    category_id: Mapped[UUID | None] = mapped_column(ForeignKey("categories.id"))
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(16), default="NORMAL")
    first_date: Mapped[date] = mapped_column(Date)
    frequency: Mapped[MaintenanceFrequency] = mapped_column(
        Enum(MaintenanceFrequency, native_enum=False, length=16)
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class MaintenanceOccurrence(Base):
    __tablename__ = "maintenance_occurrences"
    __table_args__ = (UniqueConstraint("plan_id", "scheduled_date"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    plan_id: Mapped[UUID] = mapped_column(ForeignKey("maintenance_plans.id"), index=True)
    request_id: Mapped[UUID] = mapped_column(ForeignKey("service_requests.id"), unique=True)
    scheduled_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    request_id: Mapped[UUID] = mapped_column(ForeignKey("service_requests.id"), index=True)
    author_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    internal_only: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    request_id: Mapped[UUID] = mapped_column(ForeignKey("service_requests.id"), index=True)
    uploaded_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    storage_key: Mapped[str] = mapped_column(String(512), unique=True)
    file_name: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(128))
    size_bytes: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (UniqueConstraint("organization_id", "user_id", "event_key"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    request_id: Mapped[UUID | None] = mapped_column(ForeignKey("service_requests.id"))
    event_key: Mapped[str] = mapped_column(String(160))
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    actor_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(100))
    resource_type: Mapped[str] = mapped_column(String(100))
    resource_id: Mapped[str] = mapped_column(String(64))
    before: Mapped[dict[str, object] | None] = mapped_column(JSON)
    after: Mapped[dict[str, object] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class Feedback(Base):
    __tablename__ = "feedback"
    __table_args__ = (CheckConstraint("rating between 1 and 5", name="ck_feedback_rating_range"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    request_id: Mapped[UUID] = mapped_column(ForeignKey("service_requests.id"), unique=True)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    rating: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
