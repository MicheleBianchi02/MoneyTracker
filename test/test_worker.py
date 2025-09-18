import queue
import threading
import uuid
from contextlib import contextmanager

import pytest

from src.core.domain.category import CategoryIn
from src.infrastructure.connection_pool import ConnectionPool
from src.infrastructure.job_manager import complete_task
from src.infrastructure.sqlite.unit_of_work import UnitOfWork
from src.infrastructure.task_queue import add_task, task_queue
from src.infrastructure.worker import (
    ADD_CAT_TASK_NAME,
    ADD_USER_TASK_NAME,
    END_WORKER_TASK_NAME,
    writer_worker,
)
from test.util_test import UtilTest


@pytest.fixture
def test_db_path(tmp_path):
    """Provides a path to a temporary database file."""
    return tmp_path / "test_worker.db"


@pytest.fixture
def connection_pool(test_db_path):
    """Creates a connection pool for the test database and initializes the schema."""
    pool = ConnectionPool(str(test_db_path), max_connections=5)
    with pool.managed_connection() as conn:
        with UnitOfWork(conn) as uow:
            UtilTest.init_database(uow)
    return pool


@pytest.fixture
def uow_for_test(connection_pool):
    """Provides a UnitOfWork for the main test thread to interact with the DB."""
    with connection_pool.managed_connection() as conn:
        uow = UnitOfWork(conn)
        yield uow
        uow.commit()  # Ensure changes made in test setup are saved


@pytest.fixture(autouse=True)
def worker_thread(monkeypatch, connection_pool):
    """
    Manages the lifecycle of the writer_worker thread for each test.
    """
    while not task_queue.empty():
        try:
            task_queue.get_nowait()
        except queue.Empty:
            break

    @contextmanager
    def managed_test_uow():
        with connection_pool.managed_connection() as conn:
            uow = UnitOfWork(conn)
            yield uow

    monkeypatch.setattr("src.infrastructure.worker.manage_uow", managed_test_uow)

    thread = threading.Thread(target=writer_worker, daemon=True)
    thread.start()

    yield thread

    add_task(END_WORKER_TASK_NAME, f"end_{uuid.uuid4()}", ())
    thread.join(timeout=5)
    if thread.is_alive():
        pytest.fail("Worker thread did not terminate gracefully.")


def test_worker_add_user_success(uow_for_test):
    """
    Tests that the worker can successfully process an ADD_USER task.
    """
    username = "test_user"
    password = "password123"

    args = (username, password)

    result = complete_task(ADD_USER_TASK_NAME, args, timeout=1)

    assert "id_user" in result
    user_id = result["id_user"]

    with uow_for_test:
        user_list = uow_for_test.user.get(username=username)
        assert len(user_list) == 1, "User should be persisted in the database"
        assert user_list[0].id == user_id


def test_worker_handles_multiple_tasks(uow_for_test):
    """
    Tests that the worker can process multiple different tasks sequentially.
    NOTE: This will also fail to show persisted data due to the transaction bug.
    """
    # 1. Add a user
    username = "multi_task_user"
    password = "password"
    args = (username, password)
    result = complete_task(ADD_USER_TASK_NAME, args, timeout=1)

    user_id = result["id_user"]

    # 2. Add a category for that user
    cat_in = CategoryIn(
        year=2025,
        category_type="expense",
        primary="Groceries",
        secondary=None,
    )
    args = (user_id, [cat_in])
    result = complete_task(ADD_CAT_TASK_NAME, args, timeout=1)

    assert result is None  # if not it will be something like "Timeout"

    # 3. Verify state in DB (this part will fail due to the bug)
    with uow_for_test:
        user_list = uow_for_test.user.get(username=username)
        assert len(user_list) == 1, "User should be persisted"

        cats = uow_for_test.category.get(id_user=user_id, year=2025, cat_type=None)
        assert len(cats) > 0, "Category should be persisted"
        assert cats[0].primary == "Groceries"
