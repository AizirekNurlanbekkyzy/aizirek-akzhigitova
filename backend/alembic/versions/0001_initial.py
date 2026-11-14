"""Create the complete initial FixFlow PostgreSQL schema."""
# ruff: noqa: E501

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE TABLE organizations (\n\tid UUID NOT NULL, \n\tname VARCHAR(160) NOT NULL, \n\ttimezone VARCHAR(64) NOT NULL, \n\tactive BOOLEAN NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (name)\n)"
    )
    op.execute(
        "CREATE TABLE categories (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tname VARCHAR(120) NOT NULL, \n\tactive BOOLEAN NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (organization_id, name), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n)"
    )
    op.execute(
        "CREATE TABLE idempotency_records (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tkey VARCHAR(128) NOT NULL, \n\tpayload_hash VARCHAR(64) NOT NULL, \n\tresource_id UUID NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n)"
    )
    op.execute(
        "CREATE TABLE inventory_items (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tsku VARCHAR(64) NOT NULL, \n\tname VARCHAR(160) NOT NULL, \n\tunit VARCHAR(24) NOT NULL, \n\tquantity_on_hand INTEGER NOT NULL, \n\tminimum_quantity INTEGER NOT NULL, \n\tactive BOOLEAN NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (organization_id, sku), \n\tCONSTRAINT ck_inventory_nonnegative CHECK (quantity_on_hand >= 0), \n\tCONSTRAINT ck_inventory_minimum_nonnegative CHECK (minimum_quantity >= 0), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n)"
    )
    op.execute(
        "CREATE TABLE properties (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tname VARCHAR(160) NOT NULL, \n\tcode VARCHAR(64) NOT NULL, \n\taddress VARCHAR(500) NOT NULL, \n\tactive BOOLEAN NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (organization_id, code), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n)"
    )
    op.execute(
        "CREATE TABLE skills (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tname VARCHAR(120) NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (organization_id, name), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n)"
    )
    op.execute(
        "CREATE TABLE users (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\temail VARCHAR(254) NOT NULL, \n\tpassword_hash VARCHAR(255) NOT NULL, \n\tname VARCHAR(160) NOT NULL, \n\trole VARCHAR(32) NOT NULL, \n\tactive BOOLEAN NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n)"
    )
    op.execute(
        "CREATE TABLE assets (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tproperty_id UUID NOT NULL, \n\tcategory_id UUID, \n\tasset_tag VARCHAR(64) NOT NULL, \n\tname VARCHAR(160) NOT NULL, \n\tactive BOOLEAN NOT NULL, \n\tretired_at TIMESTAMP WITH TIME ZONE, \n\tPRIMARY KEY (id), \n\tUNIQUE (organization_id, asset_tag), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tFOREIGN KEY(property_id) REFERENCES properties (id), \n\tFOREIGN KEY(category_id) REFERENCES categories (id)\n)"
    )
    op.execute(
        "CREATE TABLE audit_logs (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tactor_id UUID, \n\taction VARCHAR(100) NOT NULL, \n\tresource_type VARCHAR(100) NOT NULL, \n\tresource_id VARCHAR(64) NOT NULL, \n\tbefore JSON, \n\tafter JSON, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tFOREIGN KEY(actor_id) REFERENCES users (id)\n)"
    )
    op.execute(
        "CREATE TABLE memberships (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tuser_id UUID NOT NULL, \n\trole VARCHAR(32) NOT NULL, \n\tactive BOOLEAN NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (organization_id, user_id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tFOREIGN KEY(user_id) REFERENCES users (id)\n)"
    )
    op.execute(
        "CREATE TABLE skill_categories (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tcategory_id UUID NOT NULL, \n\tskill_id UUID NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (category_id, skill_id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tFOREIGN KEY(category_id) REFERENCES categories (id), \n\tFOREIGN KEY(skill_id) REFERENCES skills (id)\n)"
    )
    op.execute(
        "CREATE TABLE stock_movements (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\titem_id UUID NOT NULL, \n\tactor_id UUID NOT NULL, \n\tquantity_delta INTEGER NOT NULL, \n\tresulting_quantity INTEGER NOT NULL, \n\treason VARCHAR(300) NOT NULL, \n\tidempotency_key VARCHAR(128) NOT NULL, \n\tpayload_hash VARCHAR(64) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (organization_id, idempotency_key), \n\tCONSTRAINT ck_stock_movement_nonzero CHECK (quantity_delta <> 0), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tFOREIGN KEY(item_id) REFERENCES inventory_items (id), \n\tFOREIGN KEY(actor_id) REFERENCES users (id)\n)"
    )
    op.execute(
        "CREATE TABLE technicians (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tuser_id UUID NOT NULL, \n\tactive BOOLEAN NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tUNIQUE (user_id), \n\tFOREIGN KEY(user_id) REFERENCES users (id)\n)"
    )
    op.execute(
        "CREATE TABLE maintenance_plans (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tasset_id UUID NOT NULL, \n\tcategory_id UUID, \n\ttitle VARCHAR(160) NOT NULL, \n\tdescription TEXT NOT NULL, \n\tpriority VARCHAR(16) NOT NULL, \n\tfirst_date DATE NOT NULL, \n\tfrequency VARCHAR(16) NOT NULL, \n\tactive BOOLEAN NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tFOREIGN KEY(asset_id) REFERENCES assets (id), \n\tFOREIGN KEY(category_id) REFERENCES categories (id)\n)"
    )
    op.execute(
        "CREATE TABLE service_requests (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tcustomer_id UUID NOT NULL, \n\tproperty_id UUID, \n\tasset_id UUID, \n\tcategory_id UUID, \n\tdesired_visit_at TIMESTAMP WITH TIME ZONE, \n\ttitle VARCHAR(120) NOT NULL, \n\tdescription TEXT NOT NULL, \n\tpriority VARCHAR(16) NOT NULL, \n\tstatus VARCHAR(24) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tFOREIGN KEY(customer_id) REFERENCES users (id), \n\tFOREIGN KEY(property_id) REFERENCES properties (id), \n\tFOREIGN KEY(asset_id) REFERENCES assets (id), \n\tFOREIGN KEY(category_id) REFERENCES categories (id)\n)"
    )
    op.execute(
        "CREATE TABLE technician_skills (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\ttechnician_id UUID NOT NULL, \n\tskill_id UUID NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (technician_id, skill_id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tFOREIGN KEY(technician_id) REFERENCES technicians (id), \n\tFOREIGN KEY(skill_id) REFERENCES skills (id)\n)"
    )
    op.execute(
        "CREATE TABLE technician_working_hours (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\ttechnician_id UUID NOT NULL, \n\tweekday INTEGER NOT NULL, \n\tstart_minute INTEGER NOT NULL, \n\tend_minute INTEGER NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (technician_id, weekday), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tFOREIGN KEY(technician_id) REFERENCES technicians (id)\n)"
    )
    op.execute(
        "CREATE TABLE assignments (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\trequest_id UUID NOT NULL, \n\ttechnician_id UUID NOT NULL, \n\tstarts_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tends_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tstatus VARCHAR(24) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT ck_assignment_positive_duration CHECK (ends_at > starts_at), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tFOREIGN KEY(request_id) REFERENCES service_requests (id), \n\tFOREIGN KEY(technician_id) REFERENCES technicians (id)\n)"
    )
    op.execute(
        "CREATE TABLE attachments (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\trequest_id UUID NOT NULL, \n\tuploaded_by UUID NOT NULL, \n\tstorage_key VARCHAR(512) NOT NULL, \n\tfile_name VARCHAR(255) NOT NULL, \n\tcontent_type VARCHAR(128) NOT NULL, \n\tsize_bytes INTEGER NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tFOREIGN KEY(request_id) REFERENCES service_requests (id), \n\tFOREIGN KEY(uploaded_by) REFERENCES users (id), \n\tUNIQUE (storage_key)\n)"
    )
    op.execute(
        "CREATE TABLE estimates (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\trequest_id UUID NOT NULL, \n\tversion INTEGER NOT NULL, \n\tprevious_version_id UUID, \n\tstatus VARCHAR(32) NOT NULL, \n\ttotal_tyiyn INTEGER NOT NULL, \n\tcomment TEXT, \n\tcreated_by UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tdecided_at TIMESTAMP WITH TIME ZONE, \n\tPRIMARY KEY (id), \n\tUNIQUE (request_id, version), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tFOREIGN KEY(request_id) REFERENCES service_requests (id), \n\tFOREIGN KEY(previous_version_id) REFERENCES estimates (id), \n\tFOREIGN KEY(created_by) REFERENCES users (id)\n)"
    )
    op.execute(
        "CREATE TABLE feedback (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\trequest_id UUID NOT NULL, \n\tcustomer_id UUID NOT NULL, \n\trating INTEGER NOT NULL, \n\tcomment TEXT, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT ck_feedback_rating_range CHECK (rating between 1 and 5), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tUNIQUE (request_id), \n\tFOREIGN KEY(request_id) REFERENCES service_requests (id), \n\tFOREIGN KEY(customer_id) REFERENCES users (id)\n)"
    )
    op.execute(
        "CREATE TABLE maintenance_occurrences (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tplan_id UUID NOT NULL, \n\trequest_id UUID NOT NULL, \n\tscheduled_date DATE NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (plan_id, scheduled_date), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tFOREIGN KEY(plan_id) REFERENCES maintenance_plans (id), \n\tUNIQUE (request_id), \n\tFOREIGN KEY(request_id) REFERENCES service_requests (id)\n)"
    )
    op.execute(
        "CREATE TABLE material_usage (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\trequest_id UUID NOT NULL, \n\titem_id UUID NOT NULL, \n\ttechnician_id UUID NOT NULL, \n\tquantity INTEGER NOT NULL, \n\tidempotency_key VARCHAR(128) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (organization_id, idempotency_key), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tFOREIGN KEY(request_id) REFERENCES service_requests (id), \n\tFOREIGN KEY(item_id) REFERENCES inventory_items (id), \n\tFOREIGN KEY(technician_id) REFERENCES technicians (id)\n)"
    )
    op.execute(
        "CREATE TABLE notes (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\trequest_id UUID NOT NULL, \n\tauthor_id UUID NOT NULL, \n\tbody TEXT NOT NULL, \n\tinternal_only BOOLEAN NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tFOREIGN KEY(request_id) REFERENCES service_requests (id), \n\tFOREIGN KEY(author_id) REFERENCES users (id)\n)"
    )
    op.execute(
        "CREATE TABLE notifications (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tuser_id UUID NOT NULL, \n\trequest_id UUID, \n\tevent_key VARCHAR(160) NOT NULL, \n\ttitle VARCHAR(200) NOT NULL, \n\tbody TEXT NOT NULL, \n\tread_at TIMESTAMP WITH TIME ZONE, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (organization_id, user_id, event_key), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tFOREIGN KEY(user_id) REFERENCES users (id), \n\tFOREIGN KEY(request_id) REFERENCES service_requests (id)\n)"
    )
    op.execute(
        "CREATE TABLE request_events (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\trequest_id UUID NOT NULL, \n\tactor_id UUID NOT NULL, \n\tfrom_status VARCHAR(24), \n\tto_status VARCHAR(24) NOT NULL, \n\treason TEXT, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tFOREIGN KEY(request_id) REFERENCES service_requests (id), \n\tFOREIGN KEY(actor_id) REFERENCES users (id)\n)"
    )
    op.execute(
        "CREATE TABLE sla_clocks (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\trequest_id UUID NOT NULL, \n\tinitial_budget_seconds INTEGER NOT NULL, \n\tremaining_seconds INTEGER NOT NULL, \n\tstatus VARCHAR(16) NOT NULL, \n\tpaused_at TIMESTAMP WITH TIME ZONE, \n\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (request_id), \n\tCONSTRAINT ck_sla_positive_budget CHECK (initial_budget_seconds > 0), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tFOREIGN KEY(request_id) REFERENCES service_requests (id)\n)"
    )
    op.execute(
        "CREATE TABLE sla_events (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\trequest_id UUID NOT NULL, \n\tevent_type VARCHAR(32) NOT NULL, \n\tremaining_seconds INTEGER NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tFOREIGN KEY(request_id) REFERENCES service_requests (id)\n)"
    )
    op.execute(
        "CREATE TABLE assignment_events (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tassignment_id UUID NOT NULL, \n\tactor_id UUID NOT NULL, \n\tfrom_status VARCHAR(24), \n\tto_status VARCHAR(24) NOT NULL, \n\treason TEXT, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tFOREIGN KEY(assignment_id) REFERENCES assignments (id), \n\tFOREIGN KEY(actor_id) REFERENCES users (id)\n)"
    )
    op.execute(
        "CREATE TABLE estimate_events (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\testimate_id UUID NOT NULL, \n\tactor_id UUID NOT NULL, \n\tfrom_status VARCHAR(32), \n\tto_status VARCHAR(32) NOT NULL, \n\tcomment TEXT, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tFOREIGN KEY(estimate_id) REFERENCES estimates (id), \n\tFOREIGN KEY(actor_id) REFERENCES users (id)\n)"
    )
    op.execute(
        "CREATE TABLE estimate_lines (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\testimate_id UUID NOT NULL, \n\tkind VARCHAR(16) NOT NULL, \n\tdescription VARCHAR(500) NOT NULL, \n\tinventory_item_id UUID, \n\tquantity NUMERIC(12, 3) NOT NULL, \n\tunit_price_tyiyn INTEGER NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT ck_estimate_line_positive_quantity CHECK (quantity > 0), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tFOREIGN KEY(estimate_id) REFERENCES estimates (id), \n\tFOREIGN KEY(inventory_item_id) REFERENCES inventory_items (id)\n)"
    )
    op.execute("CREATE INDEX ix_categories_organization_id ON categories (organization_id)")
    op.execute(
        "CREATE INDEX ix_idempotency_records_organization_id ON idempotency_records (organization_id)"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_idempotency_org_key ON idempotency_records (organization_id, key)"
    )
    op.execute(
        "CREATE INDEX ix_inventory_items_organization_id ON inventory_items (organization_id)"
    )
    op.execute("CREATE INDEX ix_properties_organization_id ON properties (organization_id)")
    op.execute("CREATE INDEX ix_skills_organization_id ON skills (organization_id)")
    op.execute("CREATE UNIQUE INDEX ix_users_org_email ON users (organization_id, email)")
    op.execute("CREATE INDEX ix_users_organization_id ON users (organization_id)")
    op.execute("CREATE INDEX ix_assets_organization_id ON assets (organization_id)")
    op.execute("CREATE INDEX ix_assets_property_id ON assets (property_id)")
    op.execute("CREATE INDEX ix_audit_logs_organization_id ON audit_logs (organization_id)")
    op.execute("CREATE INDEX ix_memberships_organization_id ON memberships (organization_id)")
    op.execute("CREATE INDEX ix_memberships_user_id ON memberships (user_id)")
    op.execute("CREATE INDEX ix_skill_categories_category_id ON skill_categories (category_id)")
    op.execute(
        "CREATE INDEX ix_skill_categories_organization_id ON skill_categories (organization_id)"
    )
    op.execute("CREATE INDEX ix_skill_categories_skill_id ON skill_categories (skill_id)")
    op.execute(
        "CREATE INDEX ix_stock_movement_item_time ON stock_movements (organization_id, item_id, created_at)"
    )
    op.execute("CREATE INDEX ix_stock_movements_item_id ON stock_movements (item_id)")
    op.execute(
        "CREATE INDEX ix_stock_movements_organization_id ON stock_movements (organization_id)"
    )
    op.execute("CREATE INDEX ix_technicians_organization_id ON technicians (organization_id)")
    op.execute("CREATE INDEX ix_maintenance_plans_asset_id ON maintenance_plans (asset_id)")
    op.execute(
        "CREATE INDEX ix_maintenance_plans_organization_id ON maintenance_plans (organization_id)"
    )
    op.execute(
        "CREATE INDEX ix_requests_org_created ON service_requests (organization_id, created_at)"
    )
    op.execute("CREATE INDEX ix_service_requests_customer_id ON service_requests (customer_id)")
    op.execute(
        "CREATE INDEX ix_service_requests_organization_id ON service_requests (organization_id)"
    )
    op.execute(
        "CREATE INDEX ix_technician_skills_organization_id ON technician_skills (organization_id)"
    )
    op.execute("CREATE INDEX ix_technician_skills_skill_id ON technician_skills (skill_id)")
    op.execute(
        "CREATE INDEX ix_technician_skills_technician_id ON technician_skills (technician_id)"
    )
    op.execute(
        "CREATE INDEX ix_technician_working_hours_organization_id ON technician_working_hours (organization_id)"
    )
    op.execute(
        "CREATE INDEX ix_technician_working_hours_technician_id ON technician_working_hours (technician_id)"
    )
    op.execute(
        "CREATE INDEX ix_assignment_tenant_technician_time ON assignments (organization_id, technician_id, starts_at)"
    )
    op.execute("CREATE INDEX ix_assignments_organization_id ON assignments (organization_id)")
    op.execute("CREATE INDEX ix_assignments_request_id ON assignments (request_id)")
    op.execute("CREATE INDEX ix_assignments_technician_id ON assignments (technician_id)")
    op.execute("CREATE INDEX ix_attachments_organization_id ON attachments (organization_id)")
    op.execute("CREATE INDEX ix_attachments_request_id ON attachments (request_id)")
    op.execute("CREATE INDEX ix_estimates_organization_id ON estimates (organization_id)")
    op.execute("CREATE INDEX ix_estimates_request_id ON estimates (request_id)")
    op.execute("CREATE INDEX ix_feedback_organization_id ON feedback (organization_id)")
    op.execute(
        "CREATE INDEX ix_maintenance_occurrences_organization_id ON maintenance_occurrences (organization_id)"
    )
    op.execute(
        "CREATE INDEX ix_maintenance_occurrences_plan_id ON maintenance_occurrences (plan_id)"
    )
    op.execute("CREATE INDEX ix_material_usage_item_id ON material_usage (item_id)")
    op.execute("CREATE INDEX ix_material_usage_organization_id ON material_usage (organization_id)")
    op.execute("CREATE INDEX ix_material_usage_request_id ON material_usage (request_id)")
    op.execute("CREATE INDEX ix_notes_organization_id ON notes (organization_id)")
    op.execute("CREATE INDEX ix_notes_request_id ON notes (request_id)")
    op.execute("CREATE INDEX ix_notifications_organization_id ON notifications (organization_id)")
    op.execute("CREATE INDEX ix_notifications_user_id ON notifications (user_id)")
    op.execute("CREATE INDEX ix_request_events_organization_id ON request_events (organization_id)")
    op.execute("CREATE INDEX ix_request_events_request_id ON request_events (request_id)")
    op.execute("CREATE INDEX ix_sla_clocks_organization_id ON sla_clocks (organization_id)")
    op.execute("CREATE INDEX ix_sla_clocks_request_id ON sla_clocks (request_id)")
    op.execute("CREATE INDEX ix_sla_events_organization_id ON sla_events (organization_id)")
    op.execute("CREATE INDEX ix_sla_events_request_id ON sla_events (request_id)")
    op.execute(
        "CREATE INDEX ix_assignment_events_assignment_id ON assignment_events (assignment_id)"
    )
    op.execute(
        "CREATE INDEX ix_assignment_events_organization_id ON assignment_events (organization_id)"
    )
    op.execute("CREATE INDEX ix_estimate_events_estimate_id ON estimate_events (estimate_id)")
    op.execute(
        "CREATE INDEX ix_estimate_events_organization_id ON estimate_events (organization_id)"
    )
    op.execute("CREATE INDEX ix_estimate_lines_estimate_id ON estimate_lines (estimate_id)")
    op.execute("CREATE INDEX ix_estimate_lines_organization_id ON estimate_lines (organization_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS estimate_lines CASCADE")
    op.execute("DROP TABLE IF EXISTS estimate_events CASCADE")
    op.execute("DROP TABLE IF EXISTS assignment_events CASCADE")
    op.execute("DROP TABLE IF EXISTS sla_events CASCADE")
    op.execute("DROP TABLE IF EXISTS sla_clocks CASCADE")
    op.execute("DROP TABLE IF EXISTS request_events CASCADE")
    op.execute("DROP TABLE IF EXISTS notifications CASCADE")
    op.execute("DROP TABLE IF EXISTS notes CASCADE")
    op.execute("DROP TABLE IF EXISTS material_usage CASCADE")
    op.execute("DROP TABLE IF EXISTS maintenance_occurrences CASCADE")
    op.execute("DROP TABLE IF EXISTS feedback CASCADE")
    op.execute("DROP TABLE IF EXISTS estimates CASCADE")
    op.execute("DROP TABLE IF EXISTS attachments CASCADE")
    op.execute("DROP TABLE IF EXISTS assignments CASCADE")
    op.execute("DROP TABLE IF EXISTS technician_working_hours CASCADE")
    op.execute("DROP TABLE IF EXISTS technician_skills CASCADE")
    op.execute("DROP TABLE IF EXISTS service_requests CASCADE")
    op.execute("DROP TABLE IF EXISTS maintenance_plans CASCADE")
    op.execute("DROP TABLE IF EXISTS technicians CASCADE")
    op.execute("DROP TABLE IF EXISTS stock_movements CASCADE")
    op.execute("DROP TABLE IF EXISTS skill_categories CASCADE")
    op.execute("DROP TABLE IF EXISTS memberships CASCADE")
    op.execute("DROP TABLE IF EXISTS audit_logs CASCADE")
    op.execute("DROP TABLE IF EXISTS assets CASCADE")
    op.execute("DROP TABLE IF EXISTS users CASCADE")
    op.execute("DROP TABLE IF EXISTS skills CASCADE")
    op.execute("DROP TABLE IF EXISTS properties CASCADE")
    op.execute("DROP TABLE IF EXISTS inventory_items CASCADE")
    op.execute("DROP TABLE IF EXISTS idempotency_records CASCADE")
    op.execute("DROP TABLE IF EXISTS categories CASCADE")
    op.execute("DROP TABLE IF EXISTS organizations CASCADE")
