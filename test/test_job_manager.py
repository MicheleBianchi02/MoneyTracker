import random
import time
import uuid
from threading import Thread

from src.infrastructure.job_manager import (
    COMPLETED_CODE,
    FAILED_CODE,
    PENDING_CODE,
    UNKNOWN_CODE,
    JobStatusManager,
    check_status,
)
from test.util_test import UtilTest

# multiprocessing is not supported yet


def test_dict():
    job_manager = JobStatusManager()

    n_thread = 10
    n_job = 1000

    job_thread_list = []
    for _ in range(n_thread):
        job_list = []
        for _ in range(n_job):
            job_list.append(str(uuid.uuid4()))

        job_thread_list.append(job_list)

    thread_list = []
    for i in range(n_thread):
        t = Thread(target=_add_job, args=(job_manager, job_thread_list[i]))
        t.start()
        thread_list.append(t)

    for thread in thread_list:
        thread.join()

    for job_list in job_thread_list:
        for job_id in job_list:
            assert job_id in job_manager._status
            assert job_id in job_manager._journal_status

    assert len(job_manager._status.keys()) == n_thread * n_job

    thread_list = []
    for i in range(n_thread):
        t = Thread(target=_update_job, args=(job_manager, job_thread_list[i]))
        t.start()
        thread_list.append(t)

    for thread in thread_list:
        thread.join()


def test_get_status():
    job_manager = JobStatusManager()

    n_job = 10000
    n_thread = 10

    job_list = []
    for _ in range(n_job):
        job_id = str(uuid.uuid4())
        job_list.append(job_id)

        job_manager.add_job(job_id)

    status_res_list = []
    for job_id in job_list:
        status = random.choice([PENDING_CODE, FAILED_CODE])
        result = random.choice([None, UtilTest.generate_random_string()])
        job_manager.update_job(job_id, status=status, result=result)
        status_res_list.append((job_id, status, result))

    thread_list = []
    for _ in range(n_thread):
        t = Thread(target=_get_job, args=(job_manager, status_res_list))
        t.start()
        thread_list.append(t)

    for thread in thread_list:
        thread.join()

    # --- Unknown should be returned if the job_id is not present
    job_id = str(uuid.uuid4())

    status, result = job_manager.get_status(job_id)
    assert status == UNKNOWN_CODE


def test_delete_job():
    clean_sec = 4
    job_manager = JobStatusManager(cleanup_interval=clean_sec)

    n_first_job = 10000
    n_sec_job = 10000

    first_job = []
    for _ in range(n_first_job):
        job_id = str(uuid.uuid4())
        first_job.append(job_id)

        job_manager.add_job(job_id)

    time.sleep(clean_sec / 2)

    sec_job = []
    for _ in range(n_sec_job):
        job_id = str(uuid.uuid4())
        sec_job.append(job_id)

        job_manager.add_job(job_id)

    time.sleep(clean_sec / 2 + 1)

    job_manager._delete_jobs()

    for job_id in sec_job:
        assert job_id in job_manager._status
        assert job_id in job_manager._journal_status

    for job_id in first_job:
        assert job_id not in job_manager._status
        assert job_id not in job_manager._journal_status
        assert job_manager.get_status(job_id)[0] == UNKNOWN_CODE


def test_update_job():
    # the job time is increased when updating them
    job_manager = JobStatusManager(cleanup_interval=5)

    n_job = 10000
    n_upd = int(n_job / 2)

    job_list = []
    for _ in range(n_job):
        job_id = str(uuid.uuid4())
        job_list.append(job_id)

        job_manager.add_job(job_id)

    time.sleep(2)

    job_upd = random.choices(job_list, k=n_upd)

    for job_id in job_upd:
        job_manager.update_job(job_id, status=PENDING_CODE)

    time.sleep(3)

    job_manager.get_status(job_id)

    for job_id in job_list:
        if job_id in job_upd:
            assert job_id in job_manager._status
            assert job_id in job_manager._journal_status

        else:
            assert job_id not in job_manager._status
            assert job_id not in job_manager._journal_status


def test_check():
    job_manager = JobStatusManager()

    n_job = 1000
    n_upd = int(n_job / 4)

    job_list = []
    for _ in range(n_job):
        job_id = str(uuid.uuid4())
        job_list.append(job_id)

        job_manager.add_job(job_id)

    job_upd = random.choices(job_list, k=n_upd)

    for job_id in job_upd:
        status = random.choice([COMPLETED_CODE, FAILED_CODE])
        job_manager.update_job(job_id, status)

    for job_id in job_upd:
        status, result = check_status(job_id, job_manager=job_manager, timeout=1)
        assert status != UNKNOWN_CODE
        assert status != PENDING_CODE

    # --- timeout

    job_id = str(uuid.uuid4())
    job_manager.add_job(job_id)

    # Should return UNKNOWN because the job is still in pending mode when the
    # timeout is reached
    status, result = check_status(job_id, timeout=0.5, job_manager=job_manager)
    assert status == UNKNOWN_CODE

    # --- job not present

    job_id = str(uuid.uuid4())

    status, result = check_status(job_id, timeout=0.5, job_manager=job_manager)
    assert status == UNKNOWN_CODE


def test_all():
    job_manager = JobStatusManager(cleanup_interval=2)

    n_th = 10
    n_job = 1000
    n_upd = int(n_job / 2)

    job_list = []
    for _ in range(n_job):
        job_id = str(uuid.uuid4())
        job_list.append(job_id)
        job_manager.add_job(job_id)

    th_list = []
    for _ in range(n_th):
        job_add_list = []
        for _ in range(n_job):
            job_id = str(uuid.uuid4())
            job_add_list.append(job_id)
        t_a = Thread(target=_add_job, args=(job_manager, job_add_list))
        th_list.append(t_a)

        job_upd = random.choices(job_list, k=n_upd)
        t_u = Thread(target=_update_job, args=(job_manager, job_upd, False))
        th_list.append(t_u)

        status_res_list = []
        for job_id in job_list:
            # None because check_status is set to False
            status_res_list.append((job_id, None, None))

        t_g = Thread(target=_get_job, args=(job_manager, status_res_list, False))
        th_list.append(t_g)

        # we check only updated check because they are not pending
        t_check = Thread(target=_check_status, args=(job_manager, job_upd))
        th_list.append(t_check)

    for th in th_list:
        th.start()

    for th in th_list:
        th.join()


def _add_job(job_manager: JobStatusManager, job_list):
    for job_id in job_list:
        job_manager.add_job(job_id)


def _update_job(job_manager: JobStatusManager, job_list, check_status=True):
    for job_id in job_list:
        status = random.choice([FAILED_CODE, COMPLETED_CODE])
        result = random.choice([None, UtilTest.generate_random_string()])
        job_manager.update_job(job_id, status=status, result=result)

        if check_status:
            # even if there is not a lock there should not be much problem for reading,
            # it should be atomic
            assert job_manager._status[job_id] == (status, result)


def _get_job(job_manager: JobStatusManager, status_res_list: list, check_status=True):
    for job_id, status, result in status_res_list:
        status_get, result_get = job_manager.get_status(job_id)

        if check_status:
            assert status != UNKNOWN_CODE
            assert status == status_get
            assert result == result_get


def _check_status(job_manager: JobStatusManager, job_list):
    for job_id in job_list:
        status, result = check_status(job_id, job_manager=job_manager)

    assert status != UNKNOWN_CODE
