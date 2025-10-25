# sqlite VACUUM
#
# check if for each transaction, there is a corresponding exchange rate


import logging
from datetime import date, timedelta

from moneytracker.core.domain.exchange_rate import Currency
from moneytracker.core.exceptions import (
    ApiError,
    ConnectionApiError,
    RepositoryError,
    ServiceError,
    TimeOutApiError,
)
from moneytracker.core.repositories.abstract_unit_of_work import AbstractUnitOfWork
from moneytracker.core.services.app_setting_service import AppSettingService
from moneytracker.core.services.exc_rate_service import ExchangeRateService
from moneytracker.core.services.transaction_service import TransactionService
from moneytracker.core.services.user_service import UserService
from moneytracker.infrastructure.dependencies import manage_uow
from moneytracker.infrastructure.exchange_rate_provider.exchange_rate import ExchangeRateProvider
from moneytracker.infrastructure.job_manager import complete_task
from moneytracker.infrastructure.worker import (
    ADD_APP_CURRENCY_TASK_NAME,
    DELETE_EXC_RATE_TASK_NAME,
    DEPRECATION_CHECK_DATE_CONFIG_NAME,
    EDIT_APP_CURRENCY_TASK_NAME,
)

logger = logging.getLogger(__name__)


# days interval after which perform the deprecation check
DAY_DELTA_DEPRECATION_CHECK = 120


def check_deprecated(uow: AbstractUnitOfWork) -> None:
    """Check wether a currency has been deprecated.

    It is also usefull for currencies that, in the future may not be
    given by the provider (like the ISK) for long period of time, even if
    they are not deprecated.
    """

    logger.info("Checking for deprecated currencies")

    exc_provider = ExchangeRateProvider()

    try:
        last_check = uow.app_setting.get(DEPRECATION_CHECK_DATE_CONFIG_NAME)

        if last_check is not None:
            last_check = date.fromisoformat(last_check)

            if (date.today() - last_check).days < DAY_DELTA_DEPRECATION_CHECK:
                logger.info("Deprecation check terminated because insufficient time has elapsed.")
                return

        with uow:
            currencies = uow.app_setting.get_currency_list(is_active=True)

        if not currencies:
            currencies_present = False
            # if last_check is None, we should always enter this if. i.e. if there are
            # no rows in the currencies table of the db, there shouldn't be also
            # the DEPRECATION_CHECK_DATE_CONFIG_NAME row in the config table

            det_curr = exc_provider.available_currencies_detailed
            last_check = date.fromisoformat(det_curr["updated_date"])
            currencies = det_curr["currencies"]

            active_currencies_code = []
            active_currencies = []  # used only to add them in the db
            depr_currencies = []
            for curr in currencies:
                if curr["status"] == "active":
                    code = curr["code"]
                    active_currencies_code.append(code)

                    active_currencies.append(
                        Currency(
                            code=curr["code"],
                            symbol=curr["symbol"],
                            name=curr["name"],
                            is_active=True,
                            deprecation_date=None,
                        )
                    )

                else:
                    depr_date = date.fromisoformat(curr["deprecation_date"])

                    depr_currencies.append(
                        Currency(
                            code=curr["code"],
                            symbol=curr["symbol"],
                            name=curr["name"],
                            is_active=False,
                            deprecation_date=depr_date,
                        )
                    )
        else:
            currencies_present = True
            depr_currencies = []  # left empty here, used later
            active_currencies_code = [curr.code for curr in currencies]

        last_check = last_check - timedelta(days=60)
        last_check = last_check.replace(day=1)

        try:
            deprecated = exc_provider.get_deprecated_curr(active_currencies_code, last_check)
            # This should also raise ApiError when the begin_date args is not valid.
            # In this case it should never happen

        except ApiError as e:
            if isinstance(e, (TimeOutApiError, ConnectionApiError)):
                logger.error(str(e))  # only the message
            else:
                logger.exception(str(e))
            deprecated = []

        check_date = last_check

        check_date = date.today()
        check_date = check_date - timedelta(days=31)
        check_date = check_date.replace(day=1)

        curr_to_add = []
        if not currencies_present:
            dep_dict = {}
            for dep_curr in deprecated:
                dep_dict[dep_curr["code"]] = dep_curr["deprecation_date"]

            for curr in active_currencies:
                if curr.code not in dep_dict:
                    curr_to_add.append(curr)

                else:
                    curr.is_active = False
                    curr.deprecation_date = dep_dict[curr.code]
                    curr_to_add.append(curr)

            # currencies inside depr_currencies should not be returned by
            # the get_deprecated_curr of the provider because they were deprecated
            # before the "updated_date"
            curr_to_add.extend(depr_currencies)

            logger.info(
                f"Deprecation check date not present. "
                f"Adding {check_date.isoformat()} to the config table. "
                f"Adding {len(curr_to_add)} currencies."
            )
            args = (check_date, curr_to_add)
            complete_task(ADD_APP_CURRENCY_TASK_NAME, args)

        else:
            if deprecated:
                for dep_curr in deprecated:
                    dep_dict[dep_curr["code"]] = dep_curr["deprecation_date"]

                for curr in active_currencies:
                    curr.is_active = False
                    curr.deprecation_date = dep_dict[curr.code]
                    curr_to_add.append(curr)

            logger.info(f"Editing deprecated check date. Set to {check_date.isoformat()}")
            args = (check_date, curr_to_add)
            complete_task(EDIT_APP_CURRENCY_TASK_NAME, args)

        if deprecated:
            logger.info(f"Deprecated currencies have been found: {deprecated}")

            check_tr_with_dreprecated_currency()

        else:
            logger.info("No deprecated currency has been found. Check completed")

    except RepositoryError as e:
        logger.exception(str(e))
        raise ServiceError("An unexpected system error occurred.") from e


def check_tr_with_dreprecated_currency() -> None:
    logger.info("Running check on transactions and deprecated currencies")

    user_service = UserService()
    tr_service = TransactionService()
    app_setting_service = AppSettingService()

    try:
        with manage_uow() as uow:
            # if a new deprecated currency has been found, fist the currencies
            # table is modified, then this function is called

            currencies = app_setting_service.get_currencies(uow, is_active=False)

            curr_dict = {}
            for curr in currencies:
                curr_dict[curr.code] = curr.deprecation_date

            if not currencies:
                # this should not happen
                return

            user_list = user_service.get(uow, None)

            conflict_tr = []
            for user in user_list:
                tr_list, _ = tr_service.get_transaction(uow, user.id, None, None)

                for tr in tr_list:
                    if tr.currency in curr_dict and tr.tr_date >= curr_dict[tr.currency]:
                        conflict_tr.append(tr)

            if not conflict_tr:
                logger.info("No conflict for transactions. Check terminated")
                # If there are no conflict we can safely remove wrong exchange rate
                _remove_exc_rate(currencies)
                return

            logger.info(f"{len(conflict_tr)} transactions are in conflict.")
            # TODO: Fill conflict table

    except ServiceError:
        logger.error("Check terminated because of an exception.")


def _remove_exc_rate(depr_curr: list[Currency]) -> None:
    """If some exchange rates are present past the deprecation date
    they are removed."""
    exc_service = ExchangeRateService()

    with manage_uow() as uow:
        exc_rate = []
        for curr in depr_curr:
            exc_rate.extend(
                exc_service.get_rate(
                    uow,
                    begin_date=curr.deprecation_date,
                    end_date=None,
                    from_currency=None,
                    to_currency=curr.code,
                )
            )

            exc_rate.extend(
                exc_service.get_rate(
                    uow,
                    begin_date=curr.deprecation_date,
                    end_date=None,
                    from_currency=curr.code,
                    to_currency=None,
                )
            )

    logger.info(f"{len(exc_rate)} exchange rates for deprecated currencies are present")

    if exc_rate:
        args = (exc_rate,)
        complete_task(DELETE_EXC_RATE_TASK_NAME, args)

    logger.info("Exchange rate check completed.")
