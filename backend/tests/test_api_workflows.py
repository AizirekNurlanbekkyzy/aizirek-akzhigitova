from datetime import UTC, datetime, timedelta
from uuid import uuid4

from conftest import login

from app.models.entities import RequestStatus


async def test_health_and_openapi_expose_the_joined_api(api_client) -> None:
    client, _, _, _ = api_client
    live = await client.get("/health/live")
    ready = await client.get("/health/ready")
    spec = await client.get("/api/v1/openapi.json")
    assert live.json() == {"status": "ok"}
    assert ready.json() == {"status": "ready"}
    assert "/api/v1/requests/{request_id}/notes" in spec.json()["paths"]
    assert "/api/v1/assignments/{assignment_id}/accept" in spec.json()["paths"]


async def test_customer_cannot_read_another_organization_request(api_client) -> None:
    client, org_a, org_b, _ = api_client
    token_a = await login(client, "customer-a@tenant-a.example.com", org_a)
    token_b = await login(client, "customer-b@tenant-b.example.com", org_b)
    dispatcher_a = await login(client, "dispatcher-a@tenant-a.example.com", org_a)
    created = await client.post(
        "/api/v1/requests",
        headers={"Authorization": f"Bearer {token_a}", "Idempotency-Key": "tenant-a-create-001"},
        json={
            "title": "Broken lobby door",
            "description": "The main entrance door does not close securely.",
        },
    )
    assert created.status_code == 201
    hidden = await client.get(
        f"/api/v1/requests/{created.json()['id']}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    hidden_action = await client.patch(
        f"/api/v1/requests/{created.json()['id']}/status",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"status": "CANCELED"},
    )
    tenant_a_notices = await client.get(
        "/api/v1/notifications", headers={"Authorization": f"Bearer {dispatcher_a}"}
    )
    tenant_b_notices = await client.get(
        "/api/v1/notifications", headers={"Authorization": f"Bearer {token_b}"}
    )
    assert hidden.status_code == 404
    assert hidden_action.status_code == 404
    assert len(tenant_a_notices.json()["items"]) == 1
    assert tenant_b_notices.json()["items"] == []


async def test_idempotent_request_retry_returns_the_same_record(api_client) -> None:
    client, org_a, _, _ = api_client
    token = await login(client, "customer-a@tenant-a.example.com", org_a)
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": "create-request-001"}
    payload = {
        "title": "Heating issue",
        "description": "The apartment heating has stopped working.",
    }
    first = await client.post("/api/v1/requests", headers=headers, json=payload)
    replay = await client.post("/api/v1/requests", headers=headers, json=payload)
    changed = await client.post(
        "/api/v1/requests",
        headers=headers,
        json={**payload, "title": "Different heating issue"},
    )
    assert first.status_code == replay.status_code == 201
    assert first.json()["id"] == replay.json()["id"]
    assert changed.status_code == 409


async def test_request_status_transition_is_recorded(api_client) -> None:
    client, org_a, _, _ = api_client
    customer_token = await login(client, "customer-a@tenant-a.example.com", org_a)
    dispatcher_token = await login(client, "dispatcher-a@tenant-a.example.com", org_a)
    customer_headers = {"Authorization": f"Bearer {customer_token}"}
    dispatch_headers = {"Authorization": f"Bearer {dispatcher_token}"}
    created = await client.post(
        "/api/v1/requests",
        headers={
            "Authorization": f"Bearer {customer_token}",
            "Idempotency-Key": "status-create-001",
        },
        json={
            "title": "Water leak",
            "description": "A pipe under the sink is leaking onto the floor.",
        },
    )
    request_id = created.json()["id"]
    note_headers = {**customer_headers, "Idempotency-Key": "customer-note-001"}
    note_payload = {"body": "I will be available tomorrow morning."}
    note = await client.post(
        f"/api/v1/requests/{request_id}/notes", headers=note_headers, json=note_payload
    )
    note_replay = await client.post(
        f"/api/v1/requests/{request_id}/notes", headers=note_headers, json=note_payload
    )
    internal_note = await client.post(
        f"/api/v1/requests/{request_id}/notes",
        headers={**dispatch_headers, "Idempotency-Key": "dispatcher-note-001"},
        json={"body": "Call before arrival.", "internal_only": True},
    )
    customer_notes = await client.get(
        f"/api/v1/requests/{request_id}/notes", headers=customer_headers
    )
    moved = await client.patch(
        f"/api/v1/requests/{request_id}/status",
        headers={"Authorization": f"Bearer {dispatcher_token}"},
        json={"status": RequestStatus.TRIAGED.value, "reason": "Reviewed by dispatch"},
    )
    invalid = await client.patch(
        f"/api/v1/requests/{request_id}/status",
        headers={"Authorization": f"Bearer {dispatcher_token}"},
        json={"status": RequestStatus.CLOSED.value},
    )
    history = await client.get(
        f"/api/v1/requests/{request_id}/history",
        headers={"Authorization": f"Bearer {dispatcher_token}"},
    )
    assert moved.status_code == 200
    assert note.status_code == note_replay.status_code == 201
    assert note.json()["id"] == note_replay.json()["id"]
    assert internal_note.status_code == 201
    assert [entry["body"] for entry in customer_notes.json()] == [note_payload["body"]]
    assert moved.json()["status"] == RequestStatus.TRIAGED.value
    assert invalid.status_code == 409
    assert [event["to"] for event in history.json()] == ["SUBMITTED", "TRIAGED"]


async def test_unknown_organization_cannot_authenticate(api_client) -> None:
    client, org_a, _, _ = api_client
    # An unknown organization identifier is rejected before a token is issued.
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "customer-a@tenant-a.example.com",
            "password": "integration-test-password",
            "organization_id": str(uuid4()),
        },
    )
    assert response.status_code == 401


async def test_inventory_idempotency_and_nonnegative_stock(api_client) -> None:
    client, org_a, _, _ = api_client
    token = await login(client, "admin-a@tenant-a.example.com", org_a)
    headers = {"Authorization": f"Bearer {token}"}
    created = await client.post(
        "/api/v1/inventory/items",
        headers=headers,
        json={"sku": "FILTER-01", "name": "Air filter", "unit": "piece"},
    )
    item_id = created.json()["id"]
    movement_headers = {**headers, "Idempotency-Key": "stock-receive-001"}
    receive = {"quantity_delta": 5, "reason": "Initial stock receipt"}
    first = await client.post(
        f"/api/v1/inventory/items/{item_id}/movements",
        headers=movement_headers,
        json=receive,
    )
    replay = await client.post(
        f"/api/v1/inventory/items/{item_id}/movements",
        headers=movement_headers,
        json=receive,
    )
    changed = await client.post(
        f"/api/v1/inventory/items/{item_id}/movements",
        headers=movement_headers,
        json={"quantity_delta": 4, "reason": "Changed retry"},
    )
    insufficient = await client.post(
        f"/api/v1/inventory/items/{item_id}/movements",
        headers={**headers, "Idempotency-Key": "stock-issue-001"},
        json={"quantity_delta": -8, "reason": "Issue from stock"},
    )
    listing = await client.get("/api/v1/inventory/items", headers=headers)
    assert created.status_code == 201
    assert first.status_code == replay.status_code == 201
    assert first.json()["id"] == replay.json()["id"]
    assert changed.status_code == 409
    assert insufficient.status_code == 409
    assert listing.json()[0]["quantity_on_hand"] == 5


async def test_estimate_versions_are_immutable_and_require_customer_approval(api_client) -> None:
    client, org_a, _, _ = api_client
    customer_token = await login(client, "customer-a@tenant-a.example.com", org_a)
    dispatcher_token = await login(client, "dispatcher-a@tenant-a.example.com", org_a)
    customer_headers = {"Authorization": f"Bearer {customer_token}"}
    dispatcher_headers = {"Authorization": f"Bearer {dispatcher_token}"}
    request = await client.post(
        "/api/v1/requests",
        headers={**customer_headers, "Idempotency-Key": "estimate-request-001"},
        json={"title": "Boiler service", "description": "The boiler needs a service inspection."},
    )
    request_id = request.json()["id"]
    draft = {
        "comment": "Initial quote",
        "lines": [
            {
                "kind": "LABOR",
                "description": "Inspection and repair",
                "quantity": 2,
                "unit_price_tyiyn": 1250,
            }
        ],
    }
    estimate_headers = {**dispatcher_headers, "Idempotency-Key": "estimate-create-001"}
    first = await client.post(
        f"/api/v1/requests/{request_id}/estimates", headers=estimate_headers, json=draft
    )
    replay = await client.post(
        f"/api/v1/requests/{request_id}/estimates", headers=estimate_headers, json=draft
    )
    estimate_id = first.json()["id"]
    submitted = await client.post(
        f"/api/v1/estimates/{estimate_id}/submit", headers=dispatcher_headers
    )
    immutable = await client.put(
        f"/api/v1/estimates/{estimate_id}", headers=dispatcher_headers, json=draft
    )
    blocked = await client.patch(
        f"/api/v1/requests/{request_id}/status",
        headers=customer_headers,
        json={"status": "IN_PROGRESS"},
    )
    revision = await client.post(
        f"/api/v1/estimates/{estimate_id}/revise",
        headers={**dispatcher_headers, "Idempotency-Key": "estimate-revision-001"},
    )
    revised_id = revision.json()["id"]
    revised_draft = {
        **draft,
        "comment": "Updated quote",
        "lines": [{**draft["lines"][0], "unit_price_tyiyn": 1500}],
    }
    updated = await client.put(
        f"/api/v1/estimates/{revised_id}", headers=dispatcher_headers, json=revised_draft
    )
    resubmitted = await client.post(
        f"/api/v1/estimates/{revised_id}/submit", headers=dispatcher_headers
    )
    versions = await client.get(
        f"/api/v1/requests/{request_id}/estimates", headers=customer_headers
    )
    decided = await client.post(
        f"/api/v1/estimates/{revised_id}/decision",
        headers=customer_headers,
        json={"approved": True, "comment": "Approved"},
    )

    assert first.status_code == replay.status_code == 201
    assert replay.json()["id"] == estimate_id
    assert first.json()["total_tyiyn"] == 2500
    assert submitted.json()["status"] == "AWAITING_APPROVAL"
    assert immutable.status_code == 409
    assert blocked.status_code == 409
    assert revision.status_code == 201 and revision.json()["version"] == 2
    assert updated.json()["total_tyiyn"] == 3000
    assert resubmitted.json()["status"] == "AWAITING_APPROVAL"
    assert [version["status"] for version in versions.json()] == [
        "SUPERSEDED",
        "AWAITING_APPROVAL",
    ]
    assert decided.json()["status"] == "APPROVED"


async def test_schedule_accept_and_complete_technician_assignment(api_client) -> None:
    client, org_a, _, _ = api_client
    customer = await login(client, "customer-a@tenant-a.example.com", org_a)
    dispatcher = await login(client, "dispatcher-a@tenant-a.example.com", org_a)
    technician = await login(client, "technician-a@tenant-a.example.com", org_a)
    customer_headers = {"Authorization": f"Bearer {customer}"}
    dispatch_headers = {"Authorization": f"Bearer {dispatcher}"}
    technician_headers = {"Authorization": f"Bearer {technician}"}
    created = await client.post(
        "/api/v1/requests",
        headers={**customer_headers, "Idempotency-Key": "assignment-request-001"},
        json={
            "title": "Replace ceiling light",
            "description": "The ceiling light in the kitchen is not working.",
        },
    )
    request_id = created.json()["id"]
    await client.patch(
        f"/api/v1/requests/{request_id}/status",
        headers=dispatch_headers,
        json={"status": "TRIAGED"},
    )
    profile = await client.get("/api/v1/technicians/me", headers=technician_headers)
    technician_id = profile.json()["id"]
    start = (datetime.now(UTC) + timedelta(days=2)).replace(
        hour=4, minute=0, second=0, microsecond=0
    )
    window = {
        "technician_id": technician_id,
        "starts_at": start.isoformat(),
        "ends_at": (start + timedelta(hours=1)).isoformat(),
    }
    assignment = await client.post(
        f"/api/v1/requests/{request_id}/assignments",
        headers=dispatch_headers,
        json=window,
    )
    offered = assignment.json()["id"]
    technician_notices = await client.get("/api/v1/notifications", headers=technician_headers)
    assert technician_notices.json()["items"][0]["event_key"] == f"assignment.offered:{offered}"
    overlap_request = await client.post(
        "/api/v1/requests",
        headers={**customer_headers, "Idempotency-Key": "assignment-request-002"},
        json={
            "title": "Inspect kitchen tap",
            "description": "The kitchen tap pressure is low and inconsistent.",
        },
    )
    overlap_id = overlap_request.json()["id"]
    await client.patch(
        f"/api/v1/requests/{overlap_id}/status",
        headers=dispatch_headers,
        json={"status": "TRIAGED"},
    )
    overlap = await client.post(
        f"/api/v1/requests/{overlap_id}/assignments",
        headers=dispatch_headers,
        json=window,
    )
    accepted = await client.post(
        f"/api/v1/assignments/{offered}/accept", headers=technician_headers
    )
    active_tasks = await client.get("/api/v1/technician/assignments", headers=technician_headers)
    started = await client.patch(
        f"/api/v1/requests/{request_id}/status",
        headers=technician_headers,
        json={"status": "IN_PROGRESS"},
    )
    completed = await client.patch(
        f"/api/v1/requests/{request_id}/status",
        headers=technician_headers,
        json={"status": "COMPLETED"},
    )

    assert profile.status_code == 200
    assert assignment.status_code == 201
    assert overlap.status_code == 409
    assert accepted.json()["status"] == "ACCEPTED"
    assert [task["id"] for task in active_tasks.json()] == [offered]
    assert started.json()["status"] == "IN_PROGRESS"
    assert completed.json()["status"] == "COMPLETED"
