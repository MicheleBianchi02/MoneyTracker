import logging
from datetime import date

from moneytracker.core.domain.transaction import TransactionIn, TransactionOut, TransactionRepoIn
from moneytracker.core.exceptions import (
    DuplicateEntityError,
    EntityNotFoundError,
    InvalidParameterError,
    OperationNotPermittedError,
    RepositoryError,
    ServiceCategoryNotFoundError,
    ServiceError,
    ServiceExchangeRateNotFoundError,
    ServiceInvalidCurrencyError,
    ServiceTransactionNotFoundError,
)
from moneytracker.core.services.exc_rate_service import ExchangeRateService
from moneytracker.infrastructure.job_manager import (
    complete_task,
)
from moneytracker.infrastructure.sqlite.unit_of_work import UnitOfWork
from moneytracker.infrastructure.worker import (
    ADD_EXC_RATE_TASK_NAME,
    ADD_TR_TASK_NAME,
    DELETE_TR_TASK_NAME,
    EDIT_TR_TASK_NAME,
)

logger = logging.getLogger(__name__)


class TransactionService:
    def add_transaction(
        self,
        unit_of_work: UnitOfWork,
        id_user: int,
        transaction_list: list[TransactionIn] | TransactionIn,
    ) -> None:
        """Add transaction to the database.

        All transaction will be added to the user with the given id.

        Parameters
        ----------
            - id_user (int) : id of the user adding those transactions.
            - transaction_list (list or TransactionIn): List containing all the transaction
                that need to saved in the database. The argument can also be a single
                TransactionIn.

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

        logger.debug(
            f"Adding {len(list(transaction_list))} transactions to the "
            f"database for user with id_user:{id_user}"
        )

        exc_rate_service = ExchangeRateService()
        try:
            with unit_of_work as uow:
                date_list = []
                valid_tr_list = []
                for tr in transaction_list:
                    tr.currency = tr.currency.upper()
                    if not exc_rate_service.validate_currency(tr.currency):
                        logger.debug(f"{tr.currency} is not a valid currency")
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
                        logger.debug("Category not present in the database")
                        raise ServiceCategoryNotFoundError(
                            message="Category not present in the database.",
                            details={
                                "primary": tr.primary,
                                "secondary": tr.secondary,
                                "type": tr.tr_type,
                                "year": tr.tr_date.year,
                            },
                        )

                    tr = TransactionRepoIn(
                        id_user=id_user,
                        id_cat=id_cat,
                        tr_date=tr.tr_date,
                        name=tr.name,
                        value=tr.value,
                        currency=tr.currency,
                        description=tr.description,
                    )
                    valid_tr_list.append(tr)

                exc_rates = exc_rate_service.get_missing_rates(uow, date_list)

            args = (exc_rates, valid_tr_list)
            complete_task(ADD_TR_TASK_NAME, args)

        except RepositoryError as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e

    def get_transaction(
        self,
        uow: UnitOfWork,
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
            - ServiceExchangeRateNotFoundError: If an exchange rate has not been
                found in the database.
            - ServiceInvalidCurrencyError: If the given to_currency is not a valid
                currency. If None, the exception is not raised.
            - ServiceError: If something went wrong with the repository or the service.
        """

        logger.debug(f"Getting transaction list for user with id_user: {id_user}")

        exc_rate_service = ExchangeRateService()

        if order is not None:
            if order not in ["name", "date", "value", "currency", "primary", "secondary"]:
                logger.debug(f"{order} is not a valid order parameter")
                raise OperationNotPermittedError()

        if order_dir not in ["ASC", "DESC"]:
            logger.debug(f"{order_dir} is not a valid order_dir parameter")
            raise OperationNotPermittedError()

        if to_currency is not None:
            to_currency = to_currency.upper()
            if not exc_rate_service.validate_currency(to_currency):
                logger.debug(f"{to_currency} is not a valid currency")
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

        except EntityNotFoundError as e:
            # If an exchange rate is not found, try to add it
            logger.debug(f"{str(e)} : Adding missing exchange rates.")

            try:
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

                    exc_rates = exc_rate_service.get_missing_rates(uow, date_list)

                    # add exchange rates using the worker
                    args = (exc_rates,)
                    complete_task(ADD_EXC_RATE_TASK_NAME, args)

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

            except EntityNotFoundError as e:
                logger.debug(f"{str(e)}")
                raise ServiceExchangeRateNotFoundError("An exchange rate is still not found") from e

            except InvalidParameterError as e:
                logger.debug(
                    "Adding exchange rates with from_currency and to_curerncy parameters equal is prohibited"
                )
                raise ServiceError(
                    "An attempt was made to add an exchange rate with identical "
                    "from_currency and to_currency parameters, which is not allowed."
                ) from e

            except DuplicateEntityError as e:
                logger.debug("A duplicate exchange rate was added to the database")
                raise ServiceError(
                    "An attempt was made to add an already existing exchange rate",
                ) from e

            except RepositoryError as e:
                logger.exception(str(e))
                raise ServiceError("An unexpected system error occurred.") from e
        except RepositoryError as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e

    def get_summary(
        self,
        uow: UnitOfWork,
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
            ```json
            {
                prim_1: {
                    sec_1: {
                        "2020-02": 2847.2,
                        "2020-05": 3882.5,
                    },
                    sec_2: {
                        "2023-01": 565.5,
                        "2024-03": 7.7,
                    },
                },
                prim_2: {
                    N/A: {
                        "2021-01": 255.6,
                        "2022-04": 686.6,
                        "2024-05": 9023.5,
                    },
                },
            }
            ```

        Raises
        ------
            - ServiceInvalidCurrencyError: If the given to_currency is not a valid
                currency.
            - ServiceExchangeRateNotFoundError: If an exchange rate has not been
                found in the database.
            - ServiceError: If something went wrong with the repository or the service.

        """

        logger.debug(f"Getting transaction summary for user with id_user: {id_user}")

        exc_rate_service = ExchangeRateService()

        if to_currency is not None:
            to_currency = to_currency.upper()
            if not exc_rate_service.validate_currency(to_currency):
                logger.debug(f"{to_currency} is not a valid currency")
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

                    exc_rates = exc_rate_service.get_missing_rates(uow, date_list)

                    # add exchange rates using the worker
                    args = (exc_rates,)
                    complete_task(ADD_EXC_RATE_TASK_NAME, args)

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

    def get_balance(
        self,
        uow: UnitOfWork,
        id_user: int,
        to_currency: str,
        begin_date: date | None,
        end_date: date | None,
        tr_type: str | None = None,
        primary: str | None = None,
        secondary: str | None = None,
    ) -> tuple[float, float, bool]:
        """Get transaction from database in a given date range.

        The priority order is tr_type > primary > secondary. It means that if the
        primary is not None but tr_type is None, then the value of primary is ignored.
        The same is true for secondary.

        Parameters
        ----------
            - id_user (int) : id of the user
            - to_currency (str) : currency into which convert all the transactions
            - begin_date (datetime.date or None) : starting date of the date range.
                If None there is no inferior limit (all transaction up to end_date)
            - end_date (datetime.date or None) : ending date of the date range.
                If None there is no superior limit (all transaction from starting date).
            - exp_type (str or None) : type of transaction, can be 'income' or 'expense'.
                If None both type are returned. By default it is set to None,
            - primary (str or None) : primary of the required transactrions list. If None
                all transactions (indipendently on the primary) are returned.
                By default it's set to None
            - secondary (str or None) : secondary of the required transactrions list. If None
                all transactions (indipendently on the secondary) are returned. If
                this argument is not None, tr_type should not be 'income'.
                By default it's set to None.

        Returns
        -------
            A tuple containing the total expenses, the total income and a bool value
            whether the exchange rates used are up to date or not. Both the float
            values are positive (also for expenses).

        Raises
        ------
            - ServiceExchangeRateNotFoundError: If an exchange rate has not been
                found in the database.
            - ServiceInvalidCurrencyError: If the given to_currency is not a valid
                currency. If None, the exception is not raised.
            - ServiceError: If something went wrong with the repository or the service.
        """
        logger.debug(f"Getting transactions balance for user with id_user: {id_user}")

        exc_rate_service = ExchangeRateService()

        to_currency = to_currency.upper()
        if not exc_rate_service.validate_currency(to_currency):
            logger.debug(f"{to_currency} is not a valid currency")
            raise ServiceInvalidCurrencyError()

        try:
            with uow:
                tot_expe, tot_inc, is_valid = uow.transaction.get_balance(
                    id_user,
                    to_currency,
                    begin_date,
                    end_date,
                    tr_type,
                    primary,
                    secondary,
                )

            return tot_expe, tot_inc, is_valid

        except EntityNotFoundError as e:
            # If an exchange rate is not found, try to add it
            logger.error(f"{str(e)} : Adding missing exchange rates.")

            try:
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

                    exc_rates = exc_rate_service.get_missing_rates(uow, date_list)

                    # add exchange rates using the worker
                    args = (exc_rates,)
                    complete_task(ADD_EXC_RATE_TASK_NAME, args)

                with uow:
                    tot_expe, tot_inc, is_valid = uow.transaction.get_balance(
                        id_user,
                        to_currency,
                        begin_date,
                        end_date,
                        tr_type,
                        primary,
                        secondary,
                    )

                return tot_expe, tot_inc, is_valid

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
        uow: UnitOfWork,
        id_tr: int,
        new_tr: TransactionIn,
        id_user: int,
    ) -> None:
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

        logger.debug(f"Editing transaction for user with id_user: {id_user}")

        exc_rate_service = ExchangeRateService()

        new_tr.currency = new_tr.currency.upper()
        if not exc_rate_service.validate_currency(new_tr.currency):
            logger.debug(f"{new_tr.currency} is not a valid currency")
            raise ServiceInvalidCurrencyError()

        try:
            with uow:
                tr = uow.transaction.get_by_id_tr(id_tr)

                if tr is None:
                    logger.debug(f"Transaction not found with id_tr:{id_tr}")
                    raise ServiceTransactionNotFoundError(
                        """The transaction with the given id is not present in the database."""
                    )

                if tr.id_user != id_user:
                    logger.debug(
                        f"The transaction with id:{id_tr} doesn't pertain to the user with id_user:{id_user}"
                    )
                    raise OperationNotPermittedError("The transaction doesn't pertain to the user")

                if tr.tr_type != new_tr.tr_type:
                    logger.debug("Cannot change the transaction type")
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
                    logger.debug("The specified category is not present in the database.")
                    raise ServiceCategoryNotFoundError(
                        message="New category not found",
                        details={
                            "primary": new_tr.primary,
                            "secondary": new_tr.secondary,
                            "type": new_tr.tr_type,
                            "year": new_tr.tr_date.year,
                        },
                    )

                new_tr = TransactionRepoIn(
                    id_user=id_user,
                    id_cat=new_id_cat,
                    tr_date=new_tr.tr_date,
                    name=new_tr.name,
                    value=new_tr.value,
                    currency=new_tr.currency,
                    description=new_tr.description,
                )

                exc_rates = exc_rate_service.get_missing_rates(uow, [new_tr.tr_date])

            args = (id_tr, new_tr, exc_rates)
            complete_task(EDIT_TR_TASK_NAME, args)

        except RepositoryError as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e

    def delete_transaction(self, uow: UnitOfWork, id_tr: int, id_user: int) -> None:
        """Delete a transaction from the database.

        Parameters
        ----------
            - id_tr (int) : id of the transaction to be deleted.
            - id_user (int) : id of the user (used to check if the id_tr pertain to
                the given user).

        Raises
        ------
            - ServiceTransactionNotFoundError: When the transactio with the given id is not
                present in the database.
            - OperationNotPermittedError: If the transaction with id = id_tr doesn't
                have the given id_user.
            - ServiceError: If something went wrong with the repository or the service.
        """

        logger.debug(f"Deleting transaction for user with id_user: {id_user}")

        try:
            with uow:
                tr = uow.transaction.get_by_id_tr(id_tr)

            if tr is None:
                logger.debug(f"Transaction not found with id_tr:{id_tr}")
                raise ServiceTransactionNotFoundError(
                    """The transaction with the given id is not present in the database."""
                )

            if tr.id_user != id_user:
                logger.debug("The transaction doesn't pertain to the user")
                raise OperationNotPermittedError("The transaction doesn't pertain to the user")

            args = (id_tr,)
            complete_task(DELETE_TR_TASK_NAME, args)

        except RepositoryError as e:
            logger.exception(str(e))
            raise ServiceError("An unexpected system error occurred.") from e
