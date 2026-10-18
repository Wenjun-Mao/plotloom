"""Run ancestry owns currentness; timestamps are descriptive evidence only."""
from sqlalchemy import select

from ...exceptions import InvalidTransitionError
from ..schema import AutopilotRunRow


def current_run_id(links):
    predecessors = dict(links)
    if not predecessors:
        return None
    roots, children = [], {}
    for identifier, parent in predecessors.items():
        if parent is None:
            roots.append(identifier)
        elif parent not in predecessors or parent in children:
            raise ValueError("autopilot ancestry has a missing parent or multiple successors")
        else:
            children[parent] = identifier
    if len(roots) != 1:
        raise ValueError("autopilot ancestry must have exactly one root")
    visited, identifier = set(), roots[0]
    while identifier not in visited:
        visited.add(identifier)
        if identifier not in children:
            if visited != set(predecessors):
                raise ValueError("autopilot ancestry is disconnected or cyclic")
            return identifier
        identifier = children[identifier]
    raise ValueError("cyclic autopilot ancestry")


def current_run_row(session, project_id):
    rows = session.scalars(select(AutopilotRunRow).where(AutopilotRunRow.project_id == project_id)).all()
    try:
        identifier = current_run_id((row.id, row.predecessor_run_id) for row in rows)
    except ValueError as error:
        raise InvalidTransitionError("项目自动运行的继承关系无效；未授予新的执行权限。") from error
    return next((row for row in rows if row.id == identifier), None)
