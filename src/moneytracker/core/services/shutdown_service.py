from moneytracker.infrastructure.worker import end_worker


def shutdown() -> None:
    end_worker()

    # TODO: Add closing db connection. Problem is that we need to wait until the
    # worker thread ended before closing all connections

    # connection_pool.close_all()
