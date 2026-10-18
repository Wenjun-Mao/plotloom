"""Exact request/snapshot-local proof reuse, discarded on exit and SQL mutation."""
from contextlib import contextmanager
from contextvars import ContextVar

_proofs = ContextVar("project-validation-proofs", default=None)

@contextmanager
def proof_scope():
    if _proofs.get() is not None:
        yield
        return
    token = _proofs.set({})
    try:
        yield
    finally:
        _proofs.reset(token)


def geometry_proof_cache(connection, record, *, project_id, run_id, asset_home, continuation):
    cache = _proofs.get()
    if cache is None:
        return None, None
    from ..persistence.codec import stable_hash
    # Hold the connection itself: a recycled object ID must never reuse proof.
    key = (connection, connection.total_changes, connection.execute("PRAGMA data_version").fetchone()[0], project_id, run_id,
        str(asset_home) if asset_home is not None else None, continuation,
        stable_hash(record.model_dump(mode="json", by_alias=True)))
    return cache, key


def scoped_proofs(function):
    from functools import wraps
    @wraps(function)
    def scoped(*args, **kwargs):
        with proof_scope():
            return function(*args, **kwargs)
    return scoped


def retained_proof_cache(connection, name, identity):
    cache = _proofs.get()
    if cache is None:
        return None, None
    version = connection.execute("PRAGMA data_version").fetchone()[0]
    return cache, (name, connection, connection.total_changes, version, identity)


def sql_scalar(session, name, identity, calculate):
    """Reuse immutable SQL-derived scalars only within the same mutation snapshot."""
    session.flush()
    connection = session.connection().connection.driver_connection
    cache, key = retained_proof_cache(connection, name, (session.get_transaction(), session.get_nested_transaction(), identity))
    if cache is not None and key in cache:
        return cache[key]
    value = calculate()
    if cache is not None:
        cache[key] = value
    return value
