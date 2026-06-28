import logging
import uuid
from datetime import date

from moneytracker.core.exceptions import (
    DuplicateEntityError,
    EntityNotFoundError,
    ForeignKeyError,
    InvalidParameterError,
    RepositoryError,
)
from moneytracker.infrastructure.dependencies import manage_uow
from moneytracker.infrastructure.job_manager import COMPLETED_CODE, FAILED_CODE, update_status
from moneytracker.infrastructure.sqlite.unit_of_work import UnitOfWork
from moneytracker.infrastructure.task_queue import add_task, get_task

ADD_USER_TASK_NAME = "add_user"
EDIT_USER_TASK_NAME = "edit_user"
DELETE_USER_TASK_NAME = "delete_user"

ADD_CAT_TASK_NAME = "add_category"
EDIT_CAT_TASK_NAME = "edit_category"
DELETE_CAT_TASK_NAME = "delete_category"


ADD_TR_TASK_NAME = "add_transaction"
EDIT_TR_TASK_NAME = "edit_transaction"
DELETE_TR_TASK_NAME = "delete_transaction"

ADD_SETTING_TASK_NAME = "add_setting"
ADD_USER_CURRENCY_TASK_NAME = "add_user_currency"
DELETE_USER_CURRENCY_TASK_NAME = "delete_user_currency"

ADD_EXC_RATE_TASK_NAME = "add_exc_rate"
EDIT_EXC_RATE_TASK_NAME = "edit_exc_rate"
DELETE_EXC_RATE_TASK_NAME = "delete_exc_rate"

ADD_APP_SETTING_TASK_NAME = "add_app_setting"
EDIT_APP_SETTING_TASK_NAME = "edit_app_setting"
DELETE_APP_SETTING_TASK_NAME = "delete_app_setting"
ADD_APP_CURRENCY_TASK_NAME = "add_upd_app_currency"
EDIT_APP_CURRENCY_TASK_NAME = "edit_app_currency"


END_WORKER_TASK_NAME = "end_task"


# Used to add the deprecation date to the config table name
DEPRECATION_CHECK_DATE_CONFIG_NAME = "deprecation_check_date"

# This is the name of the column saved in the database. It contains the starting date
# from which the exchange rate started to get saved. This string should never change.
EXC_DATE_CONFIG_NAME = "continuous_exchange_rate_start_date"

logger = logging.getLogger(__name__)


def writer_worker(uow: UnitOfWork | None = None) -> None:
    """Function used as a thread tarket. If the uow argument is None,
    the manage_uow is used. uow can be provided when testing or when another
    thread is not to be used."""

    logger.info("Starting writer worker")

    while True:
        # Need to use his own db connection since this is a separate thread
        # Change connection every time there is a new task

        if uow is not None:
            end = _complete_task(uow)

        else:
            with manage_uow() as _uow:
                end = _complete_task(_uow)

        if end is not None:
            break


def _complete_task(uow: UnitOfWork) -> None:
    task_name, job_id, args = get_task()

    logger.debug(f"Processing writing task: {task_name}, job_id:{job_id}")

    # ------------
    # --- User ---
    # ------------

    if task_name == ADD_USER_TASK_NAME:
        try:
            username = args[0]
            hashed_password = args[1]

            with uow:
                id_user = uow.user.add(username, hashed_password)
                default_settings = uow.user_setting.get(None, None)

                for setting in default_settings:
                    uow.user_setting.add(id_user, setting.name, setting.value)

            logger.debug(f"Task completed, job_id:{job_id}")
            update_status(job_id, COMPLETED_CODE, result={"id_user": id_user})

        except (DuplicateEntityError, RepositoryError, Exception) as e:
            logger.exception(str(e))
            update_status(job_id, FAILED_CODE, str(e))

    elif task_name == EDIT_USER_TASK_NAME:
        try:
            id_user = args[0]
            username = args[1]
            password = args[2]

            with uow:
                uow.user.edit(id_user, username, password)

            logger.debug(f"Task completed, job_id:{job_id}")
            update_status(job_id, COMPLETED_CODE)

        except (
            DuplicateEntityError,
            EntityNotFoundError,
            RepositoryError,
            Exception,
        ) as e:
            logger.exception(str(e))
            update_status(job_id, FAILED_CODE, str(e))

    elif task_name == DELETE_USER_TASK_NAME:
        try:
            id_user = args[0]

            with uow:
                uow.user.delete(id_user)

            logger.debug(f"Task completed, job_id:{job_id}")
            update_status(job_id, COMPLETED_CODE)

        except (EntityNotFoundError, RepositoryError, Exception) as e:
            logger.exception(str(e))
            update_status(job_id, FAILED_CODE, str(e))

    # ----------------
    # --- Category ---
    # ----------------

    elif task_name == ADD_CAT_TASK_NAME:
        try:
            id_user = args[0]
            cat_list = args[1]

            with uow:
                uow.category.add(id_user, cat_list)

            logger.debug(f"Task completed, job_id:{job_id}")
            update_status(job_id, COMPLETED_CODE)

        except (
            InvalidParameterError,
            ForeignKeyError,
            DuplicateEntityError,
            RepositoryError,
            Exception,
        ) as e:
            logger.exception(str(e))
            update_status(job_id, FAILED_CODE, str(e))

    elif task_name == EDIT_CAT_TASK_NAME:
        try:
            id_cat = args[0]
            new_name = args[1]

            with uow:
                uow.category.edit(id_cat, new_name)

            logger.debug(f"Task completed, job_id:{job_id}")
            update_status(job_id, COMPLETED_CODE)

        except (RepositoryError, Exception) as e:
            logger.exception(str(e))
            update_status(job_id, FAILED_CODE, str(e))

    elif task_name == DELETE_CAT_TASK_NAME:
        try:
            id_cat = args[0]

            with uow:
                uow.category.delete(id_cat)

            logger.debug(f"Task completed, job_id:{job_id}")
            update_status(job_id, COMPLETED_CODE)

        except (RepositoryError, Exception) as e:
            logger.exception(str(e))
            update_status(job_id, FAILED_CODE, str(e))

    # --------------------
    # --- Transactions ---
    # --------------------

    elif task_name == ADD_TR_TASK_NAME:
        try:
            exc_rates = args[0]
            tr_list = args[1]

            # When two users have to insert a new
            # transaction for which the exchange rates are not present,
            # the service will get those rates and add them to the worker.
            # The problem is that, since the worker is in a separate thread,
            # it is possible that the same exchange rates will be missing for
            # both requests at the moment of check, and when adding them, the
            # second will see that one exchange rate is already present. For
            # this reason we added to the repo the ON CONFLICT DO UPDATE clause
            # such that, the second will just update the first without raising
            # any uniqueness error. This is obviously not the most efficient way
            # but we can suppose that this is not very likely to occour.

            with uow:
                if exc_rates:
                    uow.exchange_rate.add(exc_rates)
                uow.transaction.add(tr_list)

            logger.debug(f"Task completed, job_id:{job_id}")
            update_status(job_id, COMPLETED_CODE)

        except DuplicateEntityError as e:
            logger.error(
                "An attempt to add an exchange rate already present in the database as been made",
                exc_info=e,
            )
            update_status(job_id, FAILED_CODE, str(e))

        except (
            ForeignKeyError,
            InvalidParameterError,
            RepositoryError,
            Exception,
        ) as e:
            logger.exception(str(e))
            update_status(job_id, FAILED_CODE, str(e))

    elif task_name == EDIT_TR_TASK_NAME:
        try:
            id_tr = args[0]
            new_tr = args[1]
            exc_rates = args[2]

            with uow:
                uow.transaction.edit(id_tr, new_tr)
                if exc_rates:
                    uow.exchange_rate.add(exc_rates)

            logger.debug(f"Task completed, job_id:{job_id}")
            update_status(job_id, COMPLETED_CODE)

        except DuplicateEntityError as e:
            logger.error("A duplicate exchange rate was added to the database")
            logger.error(
                "An attempt to add an exchange rate already present in the database as been made",
                exc_info=e,
            )
            update_status(job_id, FAILED_CODE, str(e))

        except (
            ForeignKeyError,
            InvalidParameterError,
            RepositoryError,
            Exception,
        ) as e:
            logger.exception(str(e))
            update_status(job_id, FAILED_CODE, str(e))

    elif task_name == DELETE_TR_TASK_NAME:
        try:
            id_tr = args[0]

            with uow:
                uow.transaction.delete(id_tr)

            logger.debug(f"Task completed, job_id:{job_id}")
            update_status(job_id, COMPLETED_CODE)

        except (RepositoryError, Exception) as e:
            logger.exception(str(e))
            update_status(job_id, FAILED_CODE, str(e))

    # ----------------
    # --- Settings ---
    # ----------------

    elif task_name == ADD_SETTING_TASK_NAME:
        try:
            id_user = args[0]
            setting_name = args[1]
            value = args[2]

            with uow:
                uow.user_setting.add(id_user, setting_name, value)

            logger.debug(f"Task completed, job_id:{job_id}")
            update_status(job_id, COMPLETED_CODE)

        except (EntityNotFoundError, ForeignKeyError, RepositoryError, Exception) as e:
            logger.exception(str(e))
            update_status(job_id, FAILED_CODE, str(e))

    elif task_name == ADD_USER_CURRENCY_TASK_NAME:
        try:
            id_user = args[0]
            currency_code = args[1]

            with uow:
                uow.user_setting.add_user_currency(id_user, currency_code)
            logger.debug(f"Task completed, job_id:{job_id}")
            update_status(job_id, COMPLETED_CODE)

        except (DuplicateEntityError, ForeignKeyError, RepositoryError, Exception) as e:
            logger.exception(str(e))
            update_status(job_id, FAILED_CODE, str(e))

    elif task_name == DELETE_USER_CURRENCY_TASK_NAME:
        try:
            id_user = args[0]
            currency_code = args[1]

            with uow:
                uow.user_setting.delete_user_currency(id_user, currency_code)

            logger.debug(f"Task completed, job_id:{job_id}")
            update_status(job_id, COMPLETED_CODE)

        except (EntityNotFoundError, RepositoryError, Exception) as e:
            logger.exception(str(e))
            update_status(job_id, FAILED_CODE, str(e))

    # -------------------
    # --- App configs ---
    # -------------------

    elif task_name == ADD_APP_SETTING_TASK_NAME:
        try:
            exc_date_config_name = args[0]
            first_date_str = args[1]

            with uow:
                uow.app_setting.add(exc_date_config_name, first_date_str)

            logger.debug(f"Task completed, job_id:{job_id}")
            update_status(job_id, COMPLETED_CODE)

        except (DuplicateEntityError, RepositoryError, Exception) as e:
            logger.exception(str(e))
            update_status(job_id, FAILED_CODE, str(e))

    elif task_name == EDIT_APP_SETTING_TASK_NAME:
        try:
            name = args[0]
            new_value = args[1]

            with uow:
                uow.app_setting.edit(name, new_value)

            logger.debug(f"Task completed, job_id:{job_id}")
            update_status(job_id, COMPLETED_CODE)

        except (
            EntityNotFoundError,
            DuplicateEntityError,
            RepositoryError,
            Exception,
        ) as e:
            logger.exception(str(e))
            update_status(job_id, FAILED_CODE, str(e))

    elif task_name == DELETE_APP_SETTING_TASK_NAME:
        try:
            name = args[0]

            with uow:
                uow.app_setting.delete(name)

            logger.debug(f"Task completed, job_id:{job_id}")
            update_status(job_id, COMPLETED_CODE)

        except (EntityNotFoundError, RepositoryError, Exception) as e:
            logger.exception(str(e))
            update_status(job_id, FAILED_CODE, str(e))

    elif task_name == ADD_APP_CURRENCY_TASK_NAME:
        try:
            upd_date = args[0]
            currency_list = args[1]

            with uow:
                if isinstance(upd_date, date):
                    upd_date = upd_date.isoformat()

                uow.app_setting.add(DEPRECATION_CHECK_DATE_CONFIG_NAME, upd_date)
                if currency_list:
                    uow.app_setting.add_upd_currency_list(currency_list)

            logger.debug(f"Task completed, job_id:{job_id}")
            update_status(job_id, COMPLETED_CODE)

        except (DuplicateEntityError, RepositoryError, Exception) as e:
            logger.exception(str(e))
            update_status(job_id, FAILED_CODE, str(e))

    elif task_name == EDIT_APP_CURRENCY_TASK_NAME:
        try:
            upd_date = args[0]
            currency_list = args[1]

            with uow:
                if isinstance(upd_date, date):
                    upd_date = upd_date.isoformat()

                uow.app_setting.edit(DEPRECATION_CHECK_DATE_CONFIG_NAME, upd_date)
                if currency_list:
                    uow.app_setting.add_upd_currency_list(currency_list)

            logger.debug(f"Task completed, job_id:{job_id}")
            update_status(job_id, COMPLETED_CODE)

        except (EntityNotFoundError, RepositoryError, Exception) as e:
            logger.exception(str(e))
            update_status(job_id, FAILED_CODE, str(e))

    # ----------------------
    # --- Exchange rates ---
    # ----------------------

    elif task_name == ADD_EXC_RATE_TASK_NAME:
        try:
            exc_rate_list = args[0]

            with uow:
                for updated_exc in exc_rate_list:
                    uow.exchange_rate.add(updated_exc)

            logger.debug(f"Task completed, job_id:{job_id}")
            update_status(job_id, COMPLETED_CODE)

        except (InvalidParameterError, DuplicateEntityError, RepositoryError, Exception) as e:
            logger.exception(str(e))
            update_status(job_id, FAILED_CODE, str(e))

    elif task_name == EDIT_EXC_RATE_TASK_NAME:
        try:
            exc_rate_list = args[0]

            with uow:
                for updated_exc in exc_rate_list:
                    uow.exchange_rate.edit(updated_exc)

            logger.debug(f"Task completed, job_id:{job_id}")
            update_status(job_id, COMPLETED_CODE)

        except (EntityNotFoundError, RepositoryError, Exception) as e:
            logger.exception(str(e))
            update_status(job_id, FAILED_CODE, str(e))

    elif task_name == DELETE_EXC_RATE_TASK_NAME:
        try:
            exc_rate_list = args[0]

            with uow:
                # using an executemany would be more efficient
                # but we assume this will "never" occour
                for rate in exc_rate_list:
                    uow.exchange_rate.delete(rate)

            logger.debug(f"Task completed, job_id:{job_id}")
            update_status(job_id, COMPLETED_CODE)

        except (RepositoryError, Exception) as e:
            logger.exception(str(e))
            update_status(job_id, FAILED_CODE, str(e))

    # ------------------
    # --- End worker ---
    # ------------------

    elif task_name == END_WORKER_TASK_NAME:
        # When closing the applicaiton, for example with Ctrl+C, this
        # thread might be terminated abruptly, potentially leaving a database
        # transaction half-finished and corrupt
        logger.info("Closing writing worker")
        return 0


def end_worker() -> None:
    job_id = str(uuid.uuid4())
    add_task(END_WORKER_TASK_NAME, job_id, ())
