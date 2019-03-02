from flask import current_app, request, jsonify
from flask_jwt_extended import jwt_required

from marshmallow import ValidationError

from sqlalchemy.exc import IntegrityError, StatementError

from api_gateway.server.decorators import with_resource_factory, paginate
from api_gateway.executiondb.dashboard import Dashboard
from api_gateway.executiondb.schemas import DashboardSchema
from api_gateway.security import permissions_accepted_for_resources, ResourcePermissions
from api_gateway.server.problem import unique_constraint_problem, improper_json_problem, invalid_input_problem
from api_gateway.server.returncodes import *


def dashboard_getter(dashboard_id):
    return current_app.running_context.execution_db.session.query(Dashboard).filter_by(id_=dashboard_id).first()


dashboard_schema = DashboardSchema()
with_dashboard = with_resource_factory("dashboard", dashboard_getter)


@jwt_required
@permissions_accepted_for_resources(ResourcePermissions("dashboards", ["read"]))
@paginate(dashboard_schema)
def get_dashboards():
    query = current_app.running_context.execution_db.session.query(Dashboard).order_by(Dashboard.name).all()
    return query, SUCCESS


@jwt_required
@permissions_accepted_for_resources(ResourcePermissions("dashboards", ["create"]))
def create_dashboard():
    data = request.get_json()
    dashboard_name = data["name"]
    try:
        dashboard = dashboard_schema.load(data)
        current_app.running_context.execution_db.session.add(dashboard)
        current_app.running_context.execution_db.session.commit()
        return dashboard_schema.dump(dashboard), OBJECT_CREATED
    except ValidationError as e:
        current_app.running_context.execution_db.session.rollback()
        return improper_json_problem("dashboard", "create", dashboard_name, e.messages)
    except (IntegrityError, StatementError):
        current_app.running_context.execution_db.session.rollback()
        return unique_constraint_problem("dashboard", "create", dashboard_name)


@jwt_required
@permissions_accepted_for_resources(ResourcePermissions("dashboards", ["update"]))
@with_dashboard("update", "dashboard_id")
def put_dashboard(dashboard_id):
    data = request.get_json()
    errors = dashboard_schema.load(data, instance=dashboard_id).errors
    if errors:
        return invalid_input_problem("dashboard", "update", data["name"], errors)
    try:
        current_app.running_context.execution_db.session.commit()
        current_app.logger.info(f"Updated dashboard {dashboard_id}")
        return dashboard_schema.dump(dashboard_id), SUCCESS
    except (IntegrityError, StatementError):
        current_app.running_context.execution_db.session.rollback()
        return unique_constraint_problem("dashboard", "update", data["name"])


@jwt_required
@permissions_accepted_for_resources(ResourcePermissions("dashboards", ["read"]))
@with_dashboard("read", "dashboard_id")
def get_dashboard(dashboard_id):
    dashboard_json = dashboard_schema.dump(dashboard_id)
    return jsonify(dashboard_json), SUCCESS


@jwt_required
@permissions_accepted_for_resources(ResourcePermissions("dashboards", ["delete"]))
@with_dashboard("delete", "dashboard_id")
def delete_dashboard(dashboard_id):
    current_app.running_context.execution_db.session.delete(dashboard_id)
    current_app.logger.info(f"Dashboard removed: {dashboard_id.name}")
    current_app.running_context.execution_db.session.commit()
    return None, NO_CONTENT

