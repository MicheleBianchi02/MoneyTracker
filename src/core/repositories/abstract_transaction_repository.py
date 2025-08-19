from abc import ABC, abstractmethod
from datetime import date

from src.core.domain.transaction import TransactionIn, TransactionOut


class AbstractTransactionRepository(ABC):
    """Database funciton relative to transactions.

    Methods
    -------
        - add : Add list of transactions to the database
        - get : Get a list of transactions from the database
        - get_by_id : Get the transaction with the given id
        - edit : Edit a transaction already present in the database
        - delete : Delete a transaction alreadyt present in the database

    """

    @abstractmethod
    def add(self, transaction_list: list[TransactionIn] | TransactionIn) -> None:
        """
        Add transaction to the database.

        Parameters
        ----------
            - transaction_list (list or TransactionIn): List containing all the transaction
                that need to saved in the database. The argument can also be a single
                TransactionIn.

        Raises
        ------
            - EntityNotFoundError: If the id_category required is not found in the db.
            - ForeignKeyError: If a foreign key error occour (e.g. a transaction with
                a non existing id_user is added).
            - RepositoryError: If something went wrong with the database
        """

        raise NotImplementedError

    @abstractmethod
    def get(
        self,
        id_user: int,
        begin_date: date | None,
        end_date: date | None,
        tr_type: str | None = None,
        primary: str | None = None,
        secondary: str | None = None,
    ) -> list[TransactionOut]:
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
            List containing all the transaction (instances of TransactionOut). Note: even
            if there is only one transaction a list containing only one element is returned.
            If no transaction is found, an empty list is returned.

        Raises
        ------
            RepositoryError: If something went wrong with the database

        """

        raise NotImplementedError

    @abstractmethod
    def get_summary(
        self,
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
            #         None: {
            #             "2021-01": 255.6,
            #             "2022-04": 686.6,
            #             "2024-05": 9023.5,
            #         },
            #     },
            # }

        Raises
        ------
            - EntityNotFoundError: If an exchange rate is not found in the db.
            - RepostioryError: If something went wrong with the database.

        """

    @abstractmethod
    def edit(self, id_tr: int, new_tr: TransactionIn) -> None:
        """Edit a transaction.

        The only parameter that can be changed are:
        - id_category,
        - date,
        - name,
        - value,
        - description,
        - currency.

        id and id_user can't be changed.


        Parameters
        ----------
            - id_tr (int) : id of the transaction to be modified.
            - new_tr (TransactionIn) : Transaction with the new updated values.
                Even if the new Transaction has different parameter for id_user,
                the transaction is changed withoud modifing that parameter.

        Raises
        ------
            - EntityNotFounError: If the transaction with the given id_tr is not in the db.
                Or when the new category is not present in the db.
            - RepositoryError: If something went wrong with the database
        """

        raise NotImplementedError

    @abstractmethod
    def delete(self, id_tr: int) -> None:
        """Delete a transaction from the database.

        Parameters
        ----------
            id_tr (int) : id of the transaction to be deleted.

        Raises
        ------
            - EntityNotFounError: If the transaction with the given id_tr is not in the db.
            - RepositoryError: If something went wrong with the database
        """

        raise NotImplementedError
