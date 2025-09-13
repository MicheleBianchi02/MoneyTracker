import logging

from src.core.exceptions import (
    DuplicateEntityError,
    EntityNotFoundError,
    ForeignKeyError,
    InvalidParameterError,
    RepositoryError,
)
from src.infrastructure.dependencies import manage_uow
from src.infrastructure.job_manager import COMPLETED_CODE, FAILED_CODE, job_manager
from src.infrastructure.task_queue import task_queue

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
ADD_CURRENCY_TASK_NAME = "add_currency"
DELETE_CURRENCY_TASK_NAME = "delete_currency"

ADD_EXC_RATE_TASK_NAME = "add_exc_rate"
EDIT_EXC_RATE_TASK_NAME = "edit_exc_rate"

ADD_APP_CONFIG_TASK_NAME = "add_app_config"
EDIT_APP_CONFIG_TASK_NAME = "edit_app_config"
DELETE_APP_CONFIG_TASK_NAME = "delete_app_config"


END_WORKER_TASK_NAME = "end_task"


logger = logging.getLogger(__name__)


def writer_worker() -> None:
    logger.info("Starting writer worker")

    # Need to use his own db connection since this is a separate thread
    with manage_uow() as uow:
        while True:
            try:
                task_name, job_id, args = task_queue.get(block=True)

                logger.info(f"Processing writing task: {task_name}, job_id:{job_id}")

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

                        logger.info(f"Task completed, job_id:{job_id}")
                        job_manager.update_job(job_id, COMPLETED_CODE, result={"id_user": id_user})

                    except (DuplicateEntityError, RepositoryError, Exception) as e:
                        logger.exception(str(e))
                        job_manager.update_job(job_id, FAILED_CODE, str(e))

                elif task_name == EDIT_USER_TASK_NAME:
                    try:
                        id_user = args[0]
                        username = args[1]
                        password = args[2]

                        with uow:
                            uow.user.edit(id_user, username, password)

                        logger.info(f"Task completed, job_id:{job_id}")
                        job_manager.update_job(job_id, COMPLETED_CODE)

                    except (
                        DuplicateEntityError,
                        EntityNotFoundError,
                        RepositoryError,
                        Exception,
                    ) as e:
                        logger.exception(str(e))
                        job_manager.update_job(job_id, FAILED_CODE, str(e))

                elif task_name == DELETE_USER_TASK_NAME:
                    try:
                        id_user = args[0]

                        with uow:
                            uow.user.delete(id_user)

                        logger.info(f"Task completed, job_id:{job_id}")
                        job_manager.update_job(job_id, COMPLETED_CODE)

                    except (EntityNotFoundError, RepositoryError, Exception) as e:
                        logger.exception(str(e))
                        job_manager.update_job(job_id, FAILED_CODE, str(e))

                # ----------------
                # --- Category ---
                # ----------------

                elif task_name == ADD_CAT_TASK_NAME:
                    try:
                        id_user = args[0]
                        cat_list = args[1]

                        with uow:
                            uow.category.add(id_user, cat_list)

                        logger.info(f"Task completed, job_id:{job_id}")
                        job_manager.update_job(job_id, COMPLETED_CODE)

                    except (
                        InvalidParameterError,
                        ForeignKeyError,
                        DuplicateEntityError,
                        RepositoryError,
                        Exception,
                    ) as e:
                        logger.exception(str(e))
                        job_manager.update_job(job_id, FAILED_CODE, str(e))

                elif task_name == EDIT_CAT_TASK_NAME:
                    try:
                        id_cat = args[0]
                        new_name = args[1]

                        with uow:
                            uow.category.edit(id_cat, new_name)

                        logger.info(f"Task completed, job_id:{job_id}")
                        job_manager.update_job(job_id, COMPLETED_CODE)

                    except (RepositoryError, Exception) as e:
                        logger.exception(str(e))
                        job_manager.update_job(job_id, FAILED_CODE, str(e))

                elif task_name == DELETE_CAT_TASK_NAME:
                    try:
                        id_cat = args[0]

                        with uow:
                            uow.category.delete(id_cat)

                        logger.info(f"Task completed, job_id:{job_id}")
                        job_manager.update_job(job_id, COMPLETED_CODE)

                    except (RepositoryError, Exception) as e:
                        logger.exception(str(e))
                        job_manager.update_job(job_id, FAILED_CODE, str(e))

                # --------------------
                # --- Transactions ---
                # --------------------

                elif task_name == ADD_TR_TASK_NAME:
                    try:
                        exc_rates = args[0]
                        tr_list = args[1]

                        with uow:
                            if exc_rates:
                                uow.exchange_rate.add(exc_rates)
                            uow.transaction.add(tr_list)

                        logger.info(f"Task completed, job_id:{job_id}")
                        job_manager.update_job(job_id, COMPLETED_CODE)

                    except DuplicateEntityError as e:
                        logger.error(
                            "An attempt to add an exchange rate already "
                            "present in the database as been made",
                            exc_info=e,
                        )
                        job_manager.update_job(job_id, FAILED_CODE, str(e))

                    except (
                        ForeignKeyError,
                        InvalidParameterError,
                        RepositoryError,
                        Exception,
                    ) as e:
                        logger.exception(str(e))
                        job_manager.update_job(job_id, FAILED_CODE, str(e))

                elif task_name == EDIT_TR_TASK_NAME:
                    try:
                        id_tr = args[0]
                        new_tr = args[1]
                        exc_rates = args[2]

                        with uow:
                            uow.transaction.edit(id_tr, new_tr)
                            if exc_rates:
                                uow.exchange_rate.add(exc_rates)

                        logger.info(f"Task completed, job_id:{job_id}")
                        job_manager.update_job(job_id, COMPLETED_CODE)

                    except DuplicateEntityError as e:
                        logger.error("A duplicate exchange rate was added to the database")
                        logger.error(
                            "An attempt to add an exchange rate already "
                            "present in the database as been made",
                            exc_info=e,
                        )
                        job_manager.update_job(job_id, FAILED_CODE, str(e))

                    except (
                        ForeignKeyError,
                        InvalidParameterError,
                        RepositoryError,
                        Exception,
                    ) as e:
                        logger.exception(str(e))
                        job_manager.update_job(job_id, FAILED_CODE, str(e))

                elif task_name == DELETE_TR_TASK_NAME:
                    try:
                        id_tr = args[0]

                        with uow:
                            uow.transaction.delete(id_tr)

                        logger.info(f"Task completed, job_id:{job_id}")
                        job_manager.update_job(job_id, COMPLETED_CODE)

                    except (RepositoryError, Exception) as e:
                        logger.exception(str(e))
                        job_manager.update_job(job_id, FAILED_CODE, str(e))

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

                        logger.info(f"Task completed, job_id:{job_id}")
                        job_manager.update_job(job_id, COMPLETED_CODE)

                    except (EntityNotFoundError, ForeignKeyError, RepositoryError, Exception) as e:
                        logger.exception(str(e))
                        job_manager.update_job(job_id, FAILED_CODE, str(e))

                elif task_name == ADD_CURRENCY_TASK_NAME:
                    try:
                        id_user = args[0]
                        currency_code = args[1]
                        currency_symbol = args[2]

                        with uow:
                            uow.user_setting.add_currency(id_user, currency_code, currency_symbol)

                        logger.info(f"Task completed, job_id:{job_id}")
                        job_manager.update_job(job_id, COMPLETED_CODE)

                    except (DuplicateEntityError, ForeignKeyError, RepositoryError, Exception) as e:
                        logger.exception(str(e))
                        job_manager.update_job(job_id, FAILED_CODE, str(e))

                elif task_name == DELETE_CURRENCY_TASK_NAME:
                    try:
                        id_user = args[0]
                        currency_code = args[1]

                        with uow:
                            uow.user_setting.delete_currency(id_user, currency_code)

                        logger.info(f"Task completed, job_id:{job_id}")
                        job_manager.update_job(job_id, COMPLETED_CODE)

                    except (EntityNotFoundError, RepositoryError, Exception) as e:
                        logger.exception(str(e))
                        job_manager.update_job(job_id, FAILED_CODE, str(e))

                # -------------------
                # --- App configs ---
                # -------------------

                elif task_name == ADD_APP_CONFIG_TASK_NAME:
                    try:
                        exc_date_config_name = args[0]
                        first_date_str = args[1]

                        with uow:
                            uow.app_config.add(exc_date_config_name, first_date_str)

                        logger.info(f"Task completed, job_id:{job_id}")
                        job_manager.update_job(job_id, COMPLETED_CODE)

                    except (DuplicateEntityError, RepositoryError, Exception) as e:
                        logger.exception(str(e))
                        job_manager.update_job(job_id, FAILED_CODE, str(e))

                elif task_name == EDIT_APP_CONFIG_TASK_NAME:
                    try:
                        name = args[0]
                        new_value = args[1]

                        with uow:
                            uow.app_config.edit(name, new_value)

                        logger.info(f"Task completed, job_id:{job_id}")
                        job_manager.update_job(job_id, COMPLETED_CODE)

                    except (
                        EntityNotFoundError,
                        DuplicateEntityError,
                        RepositoryError,
                        Exception,
                    ) as e:
                        logger.exception(str(e))
                        job_manager.update_job(job_id, FAILED_CODE, str(e))

                elif task_name == DELETE_APP_CONFIG_TASK_NAME:
                    try:
                        name = args[0]

                        with uow:
                            uow.app_config.delete(name)

                        logger.info(f"Task completed, job_id:{job_id}")
                        job_manager.update_job(job_id, COMPLETED_CODE)

                    except (EntityNotFoundError, RepositoryError, Exception) as e:
                        logger.exception(str(e))
                        job_manager.update_job(job_id, FAILED_CODE, str(e))

                # ----------------------
                # --- Exchange rates ---
                # ----------------------

                elif task_name == ADD_EXC_RATE_TASK_NAME:
                    try:
                        exc_rate_list = args[0]

                        with uow:
                            for updated_exc in exc_rate_list:
                                uow.exchange_rate.add(updated_exc)

                        logger.info(f"Task completed, job_id:{job_id}")
                        job_manager.update_job(job_id, COMPLETED_CODE)

                    except (InvalidParameterError, DuplicateEntityError, Exception) as e:
                        logger.exception(str(e))
                        job_manager.update_job(job_id, FAILED_CODE, str(e))

                elif task_name == EDIT_EXC_RATE_TASK_NAME:
                    try:
                        exc_rate_list = args[0]

                        with uow:
                            for updated_exc in exc_rate_list:
                                uow.exchange_rate.edit(updated_exc)

                        logger.info(f"Task completed, job_id:{job_id}")
                        job_manager.update_job(job_id, COMPLETED_CODE)

                    except (EntityNotFoundError, Exception) as e:
                        logger.exception(str(e))
                        job_manager.update_job(job_id, FAILED_CODE, str(e))

                # ------------------
                # --- End worker ---
                # ------------------

                elif task_name == END_WORKER_TASK_NAME:
                    # When closing the applicaiton, for example with Ctrl+C, this
                    # thread might be terminated abruptly, potentially leaving a database
                    # transaction half-finished and corrupt
                    logger.info("Closing writing worker")
                    break

            except Exception as e:
                # TODO: Handle the job_id. Should never enter here
                logger.exception(str(e))
                continue
