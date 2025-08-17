## Transactions

If the user has only one currency. It is not needed to save the exchange rate for
that currency in the dabase. This because the currency conversion will never be needed.

## Exchange rates

To get exchange rates for a given date and currency we use the ECB API. It uses EUR as
the base currency. It means that all exchange rates will have as from_currency parameter
"EUR".
Even if the user has EUR in his currency list, it's exchange rate will not be saved in +
the database (since the rate would be one).
