"""Prevent overlapping login/logout from opening the wrong screen.

Each login attempt gets a flow id. Logout bumps that id so a splash
screen that finishes late cannot still open a dashboard.
"""

_active_flow_id = 0


def begin_auth_flow() -> int:
    global _active_flow_id
    _active_flow_id += 1
    return _active_flow_id


def invalidate_auth_flow() -> None:
    begin_auth_flow()


def is_active_auth_flow(flow_id: int) -> bool:
    return flow_id == _active_flow_id
