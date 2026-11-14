from app.domain import TRANSITIONS, RequestStatus


def test_submitted_request_can_only_be_triaged_or_canceled() -> None:
    assert TRANSITIONS[RequestStatus.SUBMITTED] == {RequestStatus.TRIAGED, RequestStatus.CANCELED}


def test_closed_request_is_terminal() -> None:
    assert not TRANSITIONS[RequestStatus.CLOSED]


def test_work_can_be_blocked_and_resumed() -> None:
    assert RequestStatus.BLOCKED in TRANSITIONS[RequestStatus.IN_PROGRESS]
    assert RequestStatus.IN_PROGRESS in TRANSITIONS[RequestStatus.BLOCKED]
