from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from threading import RLock

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from ..exceptions import BootstrapContentionError, InvalidTransitionError, LifecycleContentionError

@contextmanager
def read_lease(sessions: sessionmaker[Session]) -> Iterator[Session]:
    with sessions() as session:
        yield session

@contextmanager
def write_lease(sessions: sessionmaker[Session], write_lock: RLock) -> Iterator[Session]:
    with write_lock, sessions.begin() as session:
        yield session

def _immediate_lease(sessions: sessionmaker[Session], write_lock: RLock, *, error_factory: Callable[[], Exception], is_contention: Callable[[OperationalError], bool]) -> Iterator[Session]:
    @contextmanager
    def lease() -> Iterator[Session]:
        with write_lock, sessions() as session:
            try:
                session.connection().exec_driver_sql("BEGIN IMMEDIATE")
                yield session
                session.commit()
            except OperationalError as error:
                session.rollback()
                if is_contention(error):
                    raise error_factory() from error
                raise
            except BaseException:
                session.rollback()
                raise
    return lease()

def bootstrap_lease(sessions: sessionmaker[Session], write_lock: RLock, *, retry_after_seconds: int, is_contention: Callable[[OperationalError], bool]) -> Iterator[Session]:
    return _immediate_lease(sessions, write_lock, error_factory=lambda: BootstrapContentionError(retry_after_seconds), is_contention=is_contention)

def lifecycle_lease(sessions: sessionmaker[Session], write_lock: RLock, *, dialect_name: str, retry_after_seconds: int, is_contention: Callable[[OperationalError], bool]) -> Iterator[Session]:
    if dialect_name != "sqlite":
        return write_lease(sessions, write_lock)
    return _immediate_lease(sessions, write_lock, error_factory=lambda: LifecycleContentionError(retry_after_seconds), is_contention=is_contention)

def work_unit_claim_lease(sessions: sessionmaker[Session], write_lock: RLock, *, is_contention: Callable[[OperationalError], bool]) -> Iterator[Session]:
    return _immediate_lease(sessions, write_lock, error_factory=lambda: InvalidTransitionError("work-unit allocation is temporarily contended; retry after the active claim commits"), is_contention=is_contention)
