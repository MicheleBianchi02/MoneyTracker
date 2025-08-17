## Settings

Settings are defined in a py script shipped with the app. Every startup, after the
database is initialized those settings are loaded in the database. If already inside the
database they get updated. So, one way to add or change a default app-setting is to change
this script. In this settings table it is also possible to

## Exchange rates

The from_currency value for each exchange rate in the same rate_date must be the same.
For different dates, it can have different from_currency value.

The db doesn't allows to have the same from_currency and to_currency value, even if the
rate is 1. The ExchangeRate class, instad, allow this.

Currently, all the exchange rates are taken from the same provider (ECB API), meaning
that the from_currency parameter will have always the same value ('EUR').
The repository part is designed such that, if the provider changes, everything still work
if the exchange rate of the same date has the same from_currency value (it doesn't need
to be the same for different dates).

The first time the app is run (after installation) all the exchange rates from that date
to the first day of that year are taken from the provider and saved in the database.
If, in that moment, something went wrong with the provider (e.g. no internet connection)
the exchange rates are still saved, with fake values (e.g. rate = 1) in the database but
with the is_updated parameter set to False.
The first date of the year is saved in particular table of the database and used by the
service before adding a new transaction (see below).

At every startup, the exchange rates with the parameter is_update = False are updated
by taking the exchange rates for those dates and currencies from the provider.

Exchange rates are added to the db at sturtup. Exchange rates will be saved for every
day of the year and for every available currency (defined by the provider ~30). All
this indipendently on the users transactions's dates and preferred currencies. Saving
all possible currencies (even if the app have only 1 user with just few preferred
currencies) will increase the db size and slow down some tasks (e.g. startup,
converting transaction's value, save old transactions) but make the code much easier to
write and read, and also more mantainable.
At startup, the latest exchange rate in the db is taken, and all the exchange rates from
that date to the first available date (defined by the provider ~yesterday) are added to
the db. If there is no internet connection at startup, nothing is added.

When a transaction list is to be added to the database, we take the list of those
transaction's dates and perform some filtering.
Let's call the first date of the year in which the app was installed, begin_date.

- If the transaction's date is before this date, we first check if in the database is
  already present an exchange rate for that date. If it's not we add to the database all
  the exchange rates in a given range around that date (~all dates in the same month of
  that date). If, in that moment, something went wrong with the provider (e.g. no internet
  connection) we take exchange rate closest to that date and add it to the db, with the
  is_updated parameter set to False. This is done to still display reasonable values. If
  no exchange rate is found exchange rate with rate = 1 are still added. This should not
  happen since we added some of them at the first run (we still do that for safety reason).
- If the transaction's date is bigger than the maximum and lower than the minimum date for
  which the exchange rate are available ( ~yesterday and 2000-01-01 respectivelly), they are
  ignored.

Attention: when adding a transaction, we just check that one exchange rates exist in the
db. This can create problem if, during application's update, the available currencies
changes (e.g. by changing the provider). Infact, at startup, we don't check that, for each
date, all available currencies are present.
When the number of available currencies is changed, it's required that all the exchange
rates in the db are updated (or just add the missing exchange rates).

## Categories

There are two type of categories: income and expense. An expense can have a category
(primary) and a subcategory (secondary). Income only have primaries.
For each type two primary are not allowed to have the same name. Secondaries can
have the same name only if pertaining to different primaries (only for expenses).
An expense primary can have the same name of an income primary.
For this reason two unique index are created.

It's not necessary, for an expense's category, to have secondaries. In case the primary
is parent to some secondaries, the transaction category can't be the primary but it must
be a secondary (id_category in the transaction table should be the one of the secondary
category).

To add categories to the database it is needed to use the CategoryIn class.
In case the category is a primary (for income and expenses without secondaries) the
secondary key in the class must be set to None.

The database return a list of CategoryOut instances.

```python
class CategoryOut(BaseModel):
    id_primary: int
    id_secondary: int | None
    id_user: int
    year: int
    category_type: str
    primary: str
    secondary: str | None
```

When a primary income category is deleted, if in the database there is any transaction
with that category (same id_category), the category name is converted to a
deleted code (saved in the constant.py script), like 'sdajij3h38i98'. When the incomes
with that category are needed, the code is converted to something like 'DELETED' (depend
on the language set by the user) by the UI. This is done because a code is unique and
for an easier conversion with the language.
When the transaction with that id_category (name = code) is deleted or edited, we check
if in the database exists other transactions with that id_category. If not, the
transaction is deleted/modified and the category is deleted. If there are other income
with that category, the category is kept in the database.

If the deleted category is a secondary (expense) the process is the same as above.

It's not possible to delete a primary if there are some secondary referring to it, even
if no transactions exist with that primary. To delete an expense primary it must not
have any secondary referring to it.

## Transactions

There are two different transaction object. TransactionIn that are the transactions
coming from the UI and going to the database. TransactionOut are the transactions
going from the database to the UI. This is needed because the UI may not have
all the informations required to create the same TransactionOut, for example id key
(that is generated by the database at insert) or, if implemented, the creation_date.

```python
class TransactionIn(BaseModel):
    id_user: int
    value: float
    date: date
    name: str
    currency: str
    primary: str
    secondary: str
    description: str
```

```python
class TransactionOut(BaseModel):
    id: int
    id_user: int
    value: float
    date: date
    name: str
    currency: str
    primary: str
    secondary: str
    description: str
```

The id is automatically set by the database when inserted

In the database each transaction is saved in the transactions table as:

```sql
id_tr INTEGER PRIMARY KEY,
id_user INTEGER NOT NULL,
id_category INTEGER NOT NULL,
tr_date TEXT NOT NULL,  -- date formatted as 'YYYY-MM-DD'
name TEXT,
tr_value REAL,
description TEXT,
currency TEXT,
```

The id_category refer to the category table.
When a transaction is required, the select query will use the category table
and fill the primary and secondary key.

Transactions of type income, which doesn't have any secondary (or subcategory)
will be filled with NULL.

When the date of a transaction is edited and the year is changed, it is needed also to
change the id_category saved since categories are valid only for a certain year.
It means that the new category should be already present in the database.
