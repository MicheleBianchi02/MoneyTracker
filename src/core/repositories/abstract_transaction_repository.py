from abc import ABC, abstractmethod
from datetime import date

from core.domain.transaction import TransactionOut, TransactionRepoIn


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
    def add(self, id_user: int, tr_list: list[TransactionRepoIn]) -> None:
        """Add transaction to the database.

        All the trensactions will be added to the user with the given id_user.

        Parameters
        ----------
            - id_user (int) : id of the user for which the transactions will be added.
            - tr_list (list) : list containing TransactionRepoIn instances.
                Attention: If the id_category is not present in the database
                a ForeignKeyError is raised.

        Raises
        ------
            - ForeignKeyError: If a foreign key error occour (e.g. a transaction with
                a non existing id_user is added or the id_category doesn't exist).
            - RepositoryError: If something went wrong with the database
        """

        raise NotImplementedError

    @abstractmethod
    def get(
        self,
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
                The default value is 'ASC'.
            - limit (int or None) : number of returned transactions. Can be used when the
                transactions in the given range are a lot and a fast response is
                required. If None, the full list of transactions is returned. By default
                it's None.
            - offset (int) : starting line number after the beginning. Can be used
                when a limit is set and it is required to show the remaining
                transactions. The defualt value is 0.
            - name (str or None) : used to search transactions with name similar to
                the given value. Only the starting character are compared (ie
                if name = cine, names that will be returned are cinema, cine..., car is
                not returned). The comparison is case insensitive (ie aBcD is the same
                as AbCD) If None, the comparison is not done. None is the defualt value.

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
            - InvalidParameterError: If the order or order_dir are not allowed values.
            - RepositoryError: If something went wrong with the database.

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
            #         N/A: {
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

        raise NotImplementedError

    @abstractmethod
    def get_by_id_cat(self, id_cat: int) -> list[TransactionOut]:
        """Get transaction list with the provided category id.

        Parameters
        ----------
            - id_cat (int) : id of the category

        Returns
        -------
            List of TransactionOut instances all of which share the same category

        Raises
        ------
            RepostioryError: If something went wrong with the database.
        """

        raise NotImplementedError

    @abstractmethod
    def edit(self, id_tr: int, new_tr: TransactionRepoIn) -> None:
        """Edit a transaction.

        The only parameter that can be changed are:
        - id_category,
        - date,
        - name,
        - value,
        - description,
        - currency.

        id and id_user can't be changed.
        If the transaction with the given id is not present in the database,
        nothing is done.

        Parameters
        ----------
            - id_tr (int) : id of the transaction to be modified.
            - new_tr (TransactionIn) : Transaction with the new updated values.
                Even if the new Transaction has different parameter for id_user,
                the transaction is changed without modifing that parameter.
                Attention: If the id_category is not present in the database
                a ForeignKeyError is raised.

        Raises
        ------
            - ForeignKeyError: If the given new id_cat is not present in the database.
            - RepositoryError: If something went wrong with the database
        """

        raise NotImplementedError

    @abstractmethod
    def delete(self, id_tr: int) -> None:
        """Delete a transaction from the database.

        If the transaction with the given id is not present in the database,
        nothing is done.

        Parameters
        ----------
            id_tr (int) : id of the transaction to be deleted.

        Raises
        ------
            RepositoryError: If something went wrong with the database
        """

        raise NotImplementedError

    @abstractmethod
    def get_by_id_tr(self, id_tr: int) -> TransactionOut | None:
        """Get the transaction with  the given id_tr.

        Can be used when editing the transaction and it is need to
        validate the given paramaters (eg id_tr, id_user...).

        Parameters
        ----------
            id_tr (int) : id of the transaction

        Returns
        -------
            An instance of TransactionOut corresponding with the given id_tr.
            If nothing is found, None is returned.
        """

        raise NotImplementedError
