import calendar
from datetime import date

from src.core.domain.exchange_rate import ExchangeRate
from src.core.domain.transaction import TransactionIn
from src.core.exceptions import (
    EntityNotFoundError,
    ExchangeRateApiError,
    ForeignKeyError,
    RepositoryError,
    ServiceError,
)
from src.core.repositories.abstract_unit_of_work import AbstractUnitOfWork
from src.core.services.startup import EXC_DATE_CONFIG_NAME
from src.infrastructure.exchange_rate_provider.exchange_rate import ExchangeRateProvider

# TODO: In the api sturtup script, first the uow instance is created and after it is
# passed to this class


# TODO: Add logging


class TransactionServices:
    def add_transaction(
        self,
        unit_of_work: AbstractUnitOfWork,
        transaction_list: list[TransactionIn] | TransactionIn,
    ) -> None:
        if not isinstance(transaction_list, list):
            transaction_list = [transaction_list]

        try:
            date_list = [tr.tr_date for tr in transaction_list]

            with unit_of_work as uow:
                self._add_missing_exchange_rate(uow, date_list)

                uow.transaction.add(transaction_list)

        except EntityNotFoundError as e:
            # TODO: Since the app support multi language, this message could not
            # be displayed as is. Maybe it is better to send a numeric code or something
            # similar, and the ui will correctly understand what the problem is and
            # display the message in the correct language. Also, since this is a
            # backend, anything displayed from the UI should not be decided here.
            raise ServiceError(
                "The category for this transaction does not exist. Please create it first"
            ) from e

        except ForeignKeyError as e:
            raise ServiceError() from e

        except (RepositoryError, Exception) as e:
            raise ServiceError() from e

    def _add_missing_exchange_rate(self, uow: AbstractUnitOfWork, date_list: list[date]) -> None:
        """Add exchange rates if not already present in the database."""

        # This function will work only if in the database we always add the same number
        # of exchange rates (with the same number of currencies) for each date. Also, all
        # those exchange rates must have the same from_currency parameter.

        exc_pr = ExchangeRateProvider()

        # When the application is first run, exchange rates from a given starting date
        # to the given date are added. This below get this first date. From there, we are
        # shure that the exchange rates exist.
        exc_starting_date = uow.app_config.get(EXC_DATE_CONFIG_NAME)
        exc_starting_date = date.fromisoformat(exc_starting_date)

        date_to_check = set()  # set to remove duplicate
        for tr_date in date_list:
            if tr_date >= exc_starting_date:
                continue

            elif tr_date < exc_pr.minimum_available_date:
                continue

            else:
                # dates between minimum_date (2000-01-01) and the starting date.
                # In those cases we add exchange rates only for a given range (month)

                # Can't do tr_date.replace(days=1) since the tr_date point to the original
                # list of transactions
                date_check = date(tr_date.year, tr_date.month, 1)

                date_to_check.add(date_check)

        date_to_check = list(date_to_check)
        missing_dates = uow.exchange_rate.get_missing_rates_dates(date_to_check)

        required_dates = set()  # set to remove duplicate
        if missing_dates:
            for exc_date in missing_dates:
                year = exc_date.year
                month = exc_date.month
                last_day = calendar.monthrange(year, month)[1]
                month_date_list = [date(year, month, day) for day in range(1, last_day + 1)]

                required_dates.update(month_date_list)

            required_dates = list(required_dates)

            # this contain also the from_currency paramter.
            available_currencies = exc_pr.available_currencies

            try:
                exc_rates, not_available_exc = exc_pr.get_exchange_rate(
                    required_dates, available_currencies
                )
            except ExchangeRateApiError:
                # TODO: Add logging here

                exc_rates = []
                # Enter, for instance when there is no internet connection
                not_available_exc = {}
                not_available_exc["from_currency"] = exc_pr.base_currency
                available_currencies.remove(not_available_exc["from_currency"])

                for exc_date in missing_dates:
                    exc_date = exc_date.isoformat()
                    not_available_exc[exc_date] = available_currencies

            if len(not_available_exc.keys()) != 1:
                from_currency = not_available_exc["from_currency"]
                del not_available_exc["from_currency"]

                for exc_date, curr_list in not_available_exc.items():
                    exc_date = date.fromisoformat(exc_date)
                    cl_rate_list = uow.exchange_rate.get_closest(exc_date)

                    if cl_rate_list:
                        for cl_rate in cl_rate_list:
                            if cl_rate.to_currency in curr_list:
                                exc = ExchangeRate(
                                    from_currency=from_currency,
                                    to_currency=cl_rate.to_currency,
                                    rate=cl_rate.rate,
                                    rate_date=exc_date,
                                    is_updated=False,
                                )

                                exc_rates.append(exc)

                    else:
                        # if empty, i.e. there isn't any exchange rate in the db

                        for curr in curr_list:
                            exc = ExchangeRate(
                                from_currency=from_currency,
                                to_currency=curr,
                                rate=1,
                                rate_date=exc_date,
                                is_updated=False,
                            )

                            exc_rates.append(exc)

            uow.exchange_rate.add(exc_rates)


# def add_transaction_service(
#     uow: AbstractUnitOfWork,
#     id_user: int,
#     transaction_list: list[TransactionIn] | TransactionIn,
# ) -> None:
#     """
#     Service to handle adding a transaction and its related exchange rate if necessary.
#     """
#     try:
#         with uow:
#             uow.transaction.add(transaction_list)
#
#             if not isinstance(transaction_list, list):
#                 date_list = transaction_list.tr_date
#
#             else:
#                 date_list = [tr.tr_date for tr in transaction_list]
#
#     # --- Correct Exception Handling ---
#
#     except EntityNotFoundError as e:
#         # 1. LOG THE REAL ERROR (for developers)
#         # This gives you the full context in your logs.
#         logging.error(
#             f"Service failed: Could not find a required entity. Details: {e}", exc_info=True
#         )
#
#         # 2. RAISE A CLEAN, USER-FACING ERROR (for the UI)
#         # The UI should catch ServiceError and display this exact message.
#         # The "from e" preserves the stack trace for developers without polluting the message.
#         raise ServiceError(
#             "The category for this transaction does not exist. Please create it first."
#         ) from e
#
#     except DuplicateEntityError as e:
#         # This is not a user-facing error in our scenario, so we just log it for info
#         # and move on. The user doesn't need to know.
#         logging.info(
#             f"A duplicate exchange rate was found while adding a transaction; this is expected. Details: {e}"
#         )
#         pass
#
#     except ForeignKeyError as e:
#         # 1. LOG THE REAL ERROR
#         logging.error(
#             f"Service failed: A data integrity error occurred. Details: {e}", exc_info=True
#         )
#
#         # 2. RAISE A CLEAN, USER-FACING ERROR
#         raise ServiceError(
#             "A data consistency error occurred. Please try logging out and back in."
#         ) from e
#
#     except RepositoryError as e:
#         # 1. LOG THE REAL ERROR
#         logging.error(
#             f"An unhandled repository error occurred in the transaction service. Details: {e}",
#             exc_info=True,
#         )
#
#         # 2. RAISE A GENERIC, USER-FACING ERROR
#         raise ServiceError("An unexpected system error occurred. Please try again later.") from e
#
#
# How This Solves the Problem
#
# With this pattern:
#
#  * Your Logs will contain the rich, detailed error information. For example:
#
#  1     ERROR:root:Service failed: Could not find a required entity. Details: EntityNotFoundError("category with parameter id_user:1, tr_year:2025, ... not found.")
#  2     Traceback (most recent call last):
#  3       File "...", line ..., in add
#  4       ...
#  5     src.core.exceptions.EntityNotFoundError: category with parameter ... not found.
#
#  * Your UI Layer will catch the ServiceError and can simply do show_popup(error.message) or str(error) to get a clean, professional message ready for the user:
#     > "The category for this transaction does not exist. Please create it first."
