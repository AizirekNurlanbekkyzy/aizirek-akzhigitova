from enum import StrEnum


class Role(StrEnum):
    CUSTOMER = "CUSTOMER"
    DISPATCHER = "DISPATCHER"
    ORGANIZATION_ADMIN = "ORGANIZATION_ADMIN"
    TECHNICIAN = "TECHNICIAN"


class RequestStatus(StrEnum):
    SUBMITTED = "SUBMITTED"
    TRIAGED = "TRIAGED"
    SCHEDULED = "SCHEDULED"
    ACCEPTED = "ACCEPTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CLOSED = "CLOSED"
    CANCELED = "CANCELED"
    BLOCKED = "BLOCKED"
    REOPENED = "REOPENED"


TRANSITIONS: dict[RequestStatus, set[RequestStatus]] = {
    RequestStatus.SUBMITTED: {RequestStatus.TRIAGED, RequestStatus.CANCELED},
    RequestStatus.TRIAGED: {RequestStatus.SCHEDULED, RequestStatus.CANCELED},
    RequestStatus.SCHEDULED: {
        RequestStatus.ACCEPTED,
        RequestStatus.TRIAGED,
        RequestStatus.CANCELED,
    },
    RequestStatus.ACCEPTED: {RequestStatus.IN_PROGRESS, RequestStatus.SCHEDULED},
    RequestStatus.IN_PROGRESS: {RequestStatus.BLOCKED, RequestStatus.COMPLETED},
    RequestStatus.BLOCKED: {RequestStatus.IN_PROGRESS, RequestStatus.CANCELED},
    RequestStatus.COMPLETED: {RequestStatus.CLOSED, RequestStatus.REOPENED},
    RequestStatus.REOPENED: {RequestStatus.TRIAGED},
    RequestStatus.CLOSED: set(),
    RequestStatus.CANCELED: set(),
}
