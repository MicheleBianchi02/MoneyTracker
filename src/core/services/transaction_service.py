import calendar
import logging
import uuid
from datetime import date

from src.core.domain.exchange_rate import ExchangeRate
from src.core.domain.transaction import TransactionIn, TransactionOut
from src.core.exceptions import (
    DuplicateEntityError,
    EntityNotFoundError,
    ExchangeRateApiError,
    InvalidParameterError,
    OperationNotPermittedError,
    RepositoryError,
    ServiceCategoryNotFoundError,
    ServiceError,
    ServiceExchangeRateNotFoundError,
    ServiceInvalidCurrencyError,
    ServiceTransactionNotFoundError,
    ServiceUserNotFoundError,
)
from src.core.repositories.abstract_unit_of_work import AbstractUnitOfWork
from src.core.services.exc_rate_service import exc_rate_service
from src.core.services.startup import EXC_DATE_CONFIG_NAME
from src.infrastructure.exchange_rate_provider.exchange_rate import ExchangeRateProvider
from src.infrastructure.job_manager import (
    FAILED_CODE,
    UNKNOWN_CODE,
    check_status,
    job_manager,
)
from src.infrastructure.task_queue import task_queue
from src.infrastructure.worker import (
    ADD_EXC_RATE_TASK_NAME,
    ADD_TR_TASK_NAME,
    DELETE_TR_TASK_NAME,
    EDIT_TR_TASK_NAME,
)

logger = logging.getLogger(__name__)


class TransactionService:
    def add_transaction(
        self,
        unit_of_work: AbstractUnitOfWork,
        id_user: int,
        transaction_list: list[TransactionIn] | TransactionIn,
    ) -> str:
        """Add transaction to the database.

        All transaction will be added to the user with the given id.

        Parameters
        ----------
            - id_user (int) : id of the user adding those transactions.
            - transaction_list (list or TransactionIn): List containing all the transaction
                that need to saved in the database. The argument can also be a single
                TransactionIn.

        Returns
        -------
            The corresponding job_id. At the beginning the job_status will be pending.
            When the worker thread finished the operation, the job status get updated.

        Raises
        ------
            - ServiceInvalidCurrencyError: If the currency of the new transaction is not
                a valid currency.
            - ServiceUserNotFoundError: If the provided id_user is not present in the database.
            - ServiceCategoryNotFoundError: If the provided category is not present in the database.
            - ServiceError: If something went wrong with the repository or the service.
        """

        # TODO: Add check on name and description. There are problems in string with
        # this symbol \. Also, this -- is problematic for sqlite (sqlite3 might think
        # about it). Do it also in edit and categories.

        if not isinstance(transaction_list, list):
            transaction_list = [transaction_list]

        logger.info(f"Adding {len(list(transaction_list))} transactions to the database")

        try:
            job_id = str(uuid.uuid4())

            with unit_of_work as uow:
                try:
                    uow.user.validate_id_user(id_user)
                except EntityNotFoundError as e:
                    logger.error(f"{str(e)}")
                    raise ServiceUserNotFoundError(
                        f"The provided id_user:{id_user} is not present in the database.",
                    ) from e

                date_list = []
                valid_tr_list = []
                for tr in transaction_list:
                    tr.currency = tr.currency.upper()
                    if not exc_rate_service.validate_currency(tr.currency):
                        logger.error(f"{tr.currency} is not a valid currency")
                        raise ServiceInvalidCurrencyError()

                    date_list.append(tr.tr_date)

                    id_cat = uow.category.get_id(
                        id_user,
                        tr.tr_date.year,
                        tr.tr_type,
                        tr.primary,
                        tr.secondary,
                    )

                    if id_cat is None:
                        raise ServiceCategoryNotFoundError(
                            message="Category not present in the database.",
                            details={
                                "primary": tr.primary,
                                "secondary": tr.secondary,
                                "type": tr.tr_type,
                                "year": tr.tr_date.year,
                            },
                        )

                    valid_tr_list.append((id_cat, tr))

                exc_rates = self._get_missing_exchange_rate(uow, date_list)

            job_manager.add_job(job_id)

            args = (exc_rates, id_user, valid_tr_list)
            task_queue.put((ADD_TR_TASK_NAME, job_id, args), block=True)

            return job_id

        except RepositoryError as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e

    def get_transaction(
        self,
        uow: AbstractUnitOfWork,
        id_user: int,
        begin_date: date | None,
        end_date: date | None,
        to_currency: str | None = None,
        tr_type: str | None = None,
        primary: str | None = None,
        secondary: str | None = None,
        order: str | None = None,
        order_dir: str = "ASC",
        limit: int | None = None,
        offset: int = 0,
        name: str | None = None,
    ) -> tuple[list[TransactionOut], bool]:
        """Get transaction from database in a given date range.

        The priority order is tr_type > primary > secondary. It means that if the
        primary is not None but tr_type is None, then the value of primary is ignored.
        The same is true for secondary.

        Parameters
        ----------
            - id_user (int) : id of the user
            - begin_date (datetime.date or None) : starting date of the date range.
                If None there is no inferior limit (all transaction up to end_date)
            - end_date (datetime.date or None) : ending date of the date range.
                If None there is no superior limit (all transaction from starting date).
            - to_currency (str or None) : currency into which convert all the transaction's
                values. If None, the transactions will not be converted (returned
                with their currency). The default value is None.
            - exp_type (str or None) : type of transaction, can be 'income' or 'expense'.
                If None both type are returned. By default it is set to None,
            - primary (str or None) : primary of the required transactrions list. If None
                all transactions (indipendently on the primary) are returned.
                By default it's set to None
            - secondary (str or None) : secondary of the required transactrions list. If None
                all transactions (indipendently on the secondary) are returned. If
                this argument is not None, tr_type should not be 'income'.
                By default it's set to None.
            - order (str or None) : ordering of the returned transaction list. Can be
                one of the following values: 'name', 'date', 'value', 'currency',
                'primary', 'secondary'. If None the order is chosen by the database.
                May be needed when a limit and offset is needed with a user's required
                order. The default value is None.
            - order_dir (str) : Can be 'ASC' (for ascending) or 'DESC' (for descending).
                If order is None, this parameter is ignored. The default value is 'ASC'.
            - limit (int or None) : number of returned transactions. Can be used when the
                transactions in the given range are a lot and a fast response is
                required. If None, the full list of transactions is returned. By default
                it's None.
            - offset (int) : starting line number after the beginning. Can be used
                when a limit is set and it is required to show the remaining
                transactions. If limit is None, this parameter is ignored. The
                defualt value is 0.
            -name (str or None) : used to search transactions with name similar to
                the given value. Only the starting character are compared (ie
                if name = cine, names that will be returned are cinema, cine..., car is
                not returned). If None, the comparison is not done. None is the
                defualt value

        Returns
        -------
            List containing all the transaction (instances of TransactionOut). Note: even
            if there is only one transaction a list containing only one element is returned.
            If no transaction is found, an empty list is returned.
            It is also returned a bool value wheter the converted values of the
            transactions are updated or they exist in the database for that date. If
            to_currency is None, True is returned.

        Raises
        ------
            - OperationNotPermittedError: If the order or order_dir parameter are
                not allowed values.
            - ServiceInvalidCurrencyError: If the given to_currency is not a valid
                currency. If None, the exception is not raised.
            - ServiceError: If something went wrong with the repository or the service.
        """

        logger.info("Getting transaction list")

        if order is not None:
            if order not in ["name", "date", "value", "currency", "primary", "secondary"]:
                logger.error(f"{order} is not a valid order parameter")
                raise OperationNotPermittedError()

        if order_dir not in ["ASC", "DESC"]:
            logger.error(f"{order_dir} is not a valid order_dir parameter")
            raise OperationNotPermittedError()

        if to_currency is not None:
            to_currency = to_currency.upper()
            if not exc_rate_service.validate_currency(to_currency):
                logger.error(f"{to_currency} is not a valid currency")
                raise ServiceInvalidCurrencyError()
        try:
            with uow:
                tr_list, is_valid = uow.transaction.get(
                    id_user,
                    begin_date,
                    end_date,
                    to_currency,
                    tr_type,
                    primary,
                    secondary,
                    order,
                    order_dir,
                    limit,
                    offset,
                    name,
                )

                return tr_list, is_valid

        except (RepositoryError, Exception) as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e

    def get_summary(
        self,
        uow: AbstractUnitOfWork,
        id_user: int,
        begin_date: date | None,
        end_date: date | None,
        tr_type: str,
        to_currency: str,
        primary: str | None = None,
        secondary: str | None = None,
    ) -> tuple[dict[str, dict[str, dict[str, float]]], bool]:
        """Get transaction summary from database in a given date range.

        The priority order is primary > secondary. It means that if the secondary is not
        None but primary is None, then the value of secondary is ignored.

        Parameters
        ----------
            - id_user (int) : id of the user
            - begin_date (datetime.date or None) : starting date of the date range.
                If None there is no inferior limit (all transaction up to end_date)
            - end_date (datetime.date or None) : ending date of the date range.
                If None there is no superior limit (all transaction from starting date).
            - tr_type (str) : type of transaction, can be 'income' or 'expense'.
            - to_currency (str) : final currency into which convert all the transactions.
                It need to be a currency code (e.g. 'EUR', 'USD' ...).
            - primary (str or None) : primary of the required transactrions summary. If
                None all transactions (indipendently on the primary) are used.
                By default it's set to None
            - secondary (str or None) : secondary of the required transactrions summary.
                If None all transactions (indipendently on the secondary) are used. If
                this argument is not None, tr_type should not be 'income'.
                By default it's set to None.


        Returns
        -------
            It is returned a dictionry where the keys are the primary name, the item
            is a dictionary. The keys are the secondary names (if the transaction's
            category is a primary then this key is 'N/A') and the item is another
            dictionary. That dict has as keys the date formatted as "YYYY-MM" and
            as items the value (as float) of the total transactions for that month.
            Not all dates are present in the dictionary. If, for a certain
            category no transaction exist in that month, the key with that date is not
            present in the output.
            It is also returned a bool value to indicate if all the exchange_rates where
            updated. If at least one of the used rates wasn't updated, False is returned.

            An example is:
            # {
            #     prim_1: {
            #         sec_1: {
            #             "2020-02": 2847.2,
            #             "2020-05": 3882.5,
            #         },
            #         sec_2: {
            #             "2023-01": 565.5,
            #             "2024-03": 7.7,
            #         },
            #     },
            #     prim_2: {
            #         N/A: {
            #             "2021-01": 255.6,
            #             "2022-04": 686.6,
            #             "2024-05": 9023.5,
            #         },
            #     },
            # }

        Raises
        ------
            - ServiceInvalidCurrencyError: If the given to_currency is not a valid
                currency.
            - ServiceExchangeRateNotFoundError: If an exchange rate has not been
                found in the database.
            - ServiceError: If something went wrong with the repository or the service.

        """

        logger.info("Getting transaction summary")

        if to_currency is not None:
            to_currency = to_currency.upper()
            if not exc_rate_service.validate_currency(to_currency):
                logger.error(f"{to_currency} is not a valid currency")
                raise ServiceInvalidCurrencyError()

        try:
            with uow:
                summary, is_valid = uow.transaction.get_summary(
                    id_user,
                    begin_date,
                    end_date,
                    tr_type,
                    to_currency,
                    primary,
                    secondary,
                )

            return summary, is_valid

        except EntityNotFoundError as e:
            # If an exchange rate is not found, try to add it
            logger.error(f"{str(e)} : Adding missing exchange rates.")

            try:
                job_id = str(uuid.uuid4())
                with uow:
                    tr_list, _ = uow.transaction.get(
                        id_user=id_user,
                        begin_date=begin_date,
                        end_date=end_date,
                        tr_type=tr_type,
                        primary=primary,
                        secondary=secondary,
                    )

                    date_list = [tr.tr_date for tr in tr_list]

                    exc_rates = self._get_missing_exchange_rate(uow, date_list)

                    # add exchange rates using the worker
                    job_manager.add_job(job_id)
                    args = (exc_rates,)
                    task_queue.put((ADD_EXC_RATE_TASK_NAME, job_id, args), block=True)
                    status, _ = check_status(job_id)
                    if status == FAILED_CODE or status == UNKNOWN_CODE:
                        logger.error(
                            f"Service error - job_status:{status}, job_id:{job_id}",
                        )
                        raise ServiceError(
                            f"Service error - job_status:{status}, job_id:{job_id}",
                        )

                    summary, is_valid = uow.transaction.get_summary(
                        id_user,
                        begin_date,
                        end_date,
                        tr_type,
                        to_currency,
                        primary,
                        secondary,
                    )

                return summary, is_valid

            except EntityNotFoundError as e:
                logger.error(f"{str(e)}")
                raise ServiceExchangeRateNotFoundError("An exchange rate is still not found") from e

            except InvalidParameterError as e:
                logger.error(
                    "Adding exchange rates with from_currency and to_curerncy parameters equal is prohibited"
                )
                raise ServiceError(
                    "An attempt was made to add an exchange rate with identical "
                    "from_currency and to_currency parameters, which is not allowed."
                ) from e

            except DuplicateEntityError as e:
                logger.error("A duplicate exchange rate was added to the database")
                raise ServiceError(
                    "An attempt was made to add an already existing exchange rate",
                ) from e

            except RepositoryError as e:
                logger.exception(str(e))
                raise ServiceError("An unexpected system error occurred.") from e

        except RepositoryError as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e

    def edit_transaction(
        self,
        uow: AbstractUnitOfWork,
        id_tr: int,
        new_tr: TransactionIn,
        id_user: int,
    ) -> str:
        """Edit a transaction.

        The only parameter that can be changed are:
        - id_category,
        - date,
        - name,
        - value,
        - description,
        - currency.

        id, id_user and the type can't be changed.

        Parameters
        ----------
            - id_tr (int) : id of the transaction to be modified.
            - new_tr (TransactionIn) : Transaction with the new updated values.
                Attention: The new id_category is found using the id_user, tr_date,
                primary, secondary inside the new_tr. If those parameter are inconsitend
                the wrong id_category may be returned.
            - id_user (int) : id of the user (used to check if the id_tr pertain to
                the given user).

        Returns
        -------
            The corresponding job_id. At the beginning the job_status will be pending.
            When the worker thread finished the operation, the job status get updated.

        Raises
        ------
            - ServiceInvalidCurrencyError: If the new currency is not a valid
                currency.
            - ServiceTransactionNotFoundError: When the transactio with the given id is not
                present in the database.
            - ServiceCategoryNotFoundError: If the new category is not present in
                the database.
            - OperationNotPermittedError: If the transaction with id = id_tr doesn't
                have the given id_user.
            - ServiceError: If something went wrong with the repository or the service.
        """

        logger.info("Editing transaction")
        new_tr.currency = new_tr.currency.upper()
        if not exc_rate_service.validate_currency(new_tr.currency):
            logger.error(f"{new_tr.currency} is not a valid currency")
            raise ServiceInvalidCurrencyError()

        try:
            job_id = str(uuid.uuid4())
            with uow:
                tr = uow.transaction.get_by_id_tr(id_tr)

                if tr is None:
                    logger.error(f"Transaction not found with id_tr:{id_tr}")
                    raise ServiceTransactionNotFoundError(
                        """The transaction with the given id is not present in the database."""
                    )

                if tr.id_user != id_user:
                    logger.error(
                        f"The transaction with id:{id_tr} doesn't pertain to the user with id_user:{id_user}"
                    )
                    raise OperationNotPermittedError("The transaction doesn't pertain to the user")

                if tr.tr_type != new_tr.tr_type:
                    logger.error("Cannot change the transaction type")
                    raise OperationNotPermittedError("Cannot change the transaction type")

                # if the category parameter didn't change, the old id is returned
                new_id_cat = uow.category.get_id(
                    id_user=id_user,
                    year=new_tr.tr_date.year,
                    cat_type=new_tr.tr_type,
                    primary=new_tr.primary,
                    secondary=new_tr.secondary,
                )

                if new_id_cat is None:
                    logger.error("The specified category is not present in the database.")
                    raise ServiceCategoryNotFoundError(
                        message="New category not found",
                        details={
                            "primary": new_tr.primary,
                            "secondary": new_tr.secondary,
                            "type": new_tr.tr_type,
                            "year": new_tr.tr_date.year,
                        },
                    )

                exc_rates = self._get_missing_exchange_rate(uow, [new_tr.tr_date])

            job_manager.add_job(job_id)

            args = (id_tr, new_id_cat, new_tr, exc_rates)
            task_queue.put((EDIT_TR_TASK_NAME, job_id, args), block=True)

            return job_id

        except RepositoryError as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e

    def delete_transaction(self, uow: AbstractUnitOfWork, id_tr: int, id_user: int) -> str:
        """Delete a transaction from the database.

        Parameters
        ----------
            - id_tr (int) : id of the transaction to be deleted.
            - id_user (int) : id of the user (used to check if the id_tr pertain to
                the given user).

        Returns
        -------
            The corresponding job_id. At the beginning the job_status will be pending.
            When the worker thread finished the operation, the job status get updated.

        Raises
        ------
            - ServiceTransactionNotFoundError: When the transactio with the given id is not
                present in the database.
            - OperationNotPermittedError: If the transaction with id = id_tr doesn't
                have the given id_user.
            - ServiceError: If something went wrong with the repository or the service.
        """

        logger.info("Deleting transaction")

        try:
            job_id = str(uuid.uuid4())

            with uow:
                tr = uow.transaction.get_by_id_tr(id_tr)

            if tr.id_user != id_user:
                logger.error("The transaction doesn't pertain to the user")
                raise OperationNotPermittedError("The transaction doesn't pertain to the user")

            if tr is None:
                logger.error(f"Transaction not found with id_tr:{id_tr}")
                raise ServiceTransactionNotFoundError(
                    """The transaction with the given id is not present in the database."""
                )

            job_manager.add_job(job_id)
            args = (id_tr,)
            task_queue.put((DELETE_TR_TASK_NAME, job_id, args), block=True)

            return job_id

        except RepositoryError as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e

    def _get_missing_exchange_rate(
        self,
        uow: AbstractUnitOfWork,
        date_list: list[date],
    ) -> list[ExchangeRate]:
        """Get missing exchange rates based on the given date_list"""

        # This function will work only if in the database we always add the same number
        # of exchange rates (with the same number of currencies) for each date. Also, all
        # those exchange rates must have the same from_currency parameter.

        exc_pr = ExchangeRateProvider()

        # When the application is first run, exchange rates from a given starting date
        # to the given date are added. This below get this first date. From there, we are
        # sure that the exchange rates exist. If, for any reason, that date is not
        # present in the datebase, we don't save any exchange rate (this should not
        # happen since it can lead to some error).
        exc_starting_date = uow.app_config.get(EXC_DATE_CONFIG_NAME)
        if exc_starting_date is None:
            exc_starting_date = date(1, 1, 1)

        else:
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
        exc_rates = []
        if missing_dates:
            for exc_date in missing_dates:
                year = exc_date.year
                month = exc_date.month
                last_day = calendar.monthrange(year, month)[1]
                month_date_list = [date(year, month, day) for day in range(1, last_day + 1)]

                required_dates.update(month_date_list)

            required_dates = list(required_dates)

            # this contain also the from_currency parameter.
            available_currencies = exc_pr.available_currencies

            try:
                exc_rates, not_available_exc = exc_pr.get_exchange_rate(
                    required_dates, available_currencies
                )
            except ExchangeRateApiError as e:
                logger.exception(str(e))

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

        return exc_rates
