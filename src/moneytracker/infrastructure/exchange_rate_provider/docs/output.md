------ ECB API ----
The time needed for each request is around 0.11 second. The number of currencies and
the day doesn't influence a lot the time required. If the date is very old more time
could be necessary

An example of a possible output is in the docs. It follow a brief explanation:

```json
"0:2:0:0:0": {
    "attributes": [
        0,
        null,
        0,
        null,
        null,
        null,
        null,
        null,
        null,
        null,
        null,
        null,
        0,
        null,
        0,
        null,
        2,
        2,
        2,
        0
    ],
    "observations": {
        "0": [
            null,
            0,
            null,
            null,
            null
        ],
        "1": [
            1.6682,
            1,
            null,
            null,
            null
        ],
        "2": [
            1.6604,
            1,
            null,
            null,
            null
        ],
        "3": [
            1.6547,
            1,
            null,
            null,
            null
        ],
        "4": [
            null,
            0,
            null,
            null,
            null
        ]
    }
```

::::::::::
"0:2:0:0:0": The 2 is the code referring at the currency. The list is at the end.
An example of that list is (in this case the currency is CHF):

```json
{
    "id": "CURRENCY",
    "name": "Currency",
    "values": [
        {
            "id": "AUD",
            "name": "Australian dollar"
        },
        {
            "id": "CAD",
            "name": "Canadian dollar"
        },
        {
            "id": "CHF",
            "name": "Swiss franc"
        },
        {
            "id": "CNY",
            "name": "Chinese yuan renminbi"
        },
        {
            "id": "GBP",
            "name": "UK pound sterling"
        },
        {
            "id": "JPY",
            "name": "Japanese yen"
        },
        {
            "id": "USD",
            "name": "US dollar"
        }
    ]
},
```

::::::::::
The keys of "observations" are the days considered. The list is at the end.
Weekends normaly are not present. An example of that list is
("0" = "2007-12-26", "1" = "2007-12-27", ...):

```json
"values": [
            {
                "id": "2007-12-26",
                "name": "2007-12-26",
                "start": "2007-12-26T00:00:00.000+01:00",
                "end": "2007-12-26T23:59:59.999+01:00"
            },
            {
                "id": "2007-12-27",
                "name": "2007-12-27",
                "start": "2007-12-27T00:00:00.000+01:00",
                "end": "2007-12-27T23:59:59.999+01:00"
            },
            {
                "id": "2007-12-28",
                "name": "2007-12-28",
                "start": "2007-12-28T00:00:00.000+01:00",
                "end": "2007-12-28T23:59:59.999+01:00"
            },
            {
                "id": "2007-12-31",
                "name": "2007-12-31",
                "start": "2007-12-31T00:00:00.000+01:00",
                "end": "2007-12-31T23:59:59.999+01:00"
            },
            {
                "id": "2008-01-01",
                "name": "2008-01-01",
                "start": "2008-01-01T00:00:00.000+01:00",
                "end": "2008-01-01T23:59:59.999+01:00"
            }
        ]
```

::::::::::
For the list inside the keys of "observations" can be of two type:

```json
{
    "id": "OBS_STATUS",
    "name": "Observation status",
    "values": [
        {
            "id": "H",
            "name": "Missing value; holiday or weekend"
        },
        {
            "id": "A",
            "name": "Normal value"
        }
    ]
},
```

If the date is an holiday we will have a 0 in the second entry of the list,
otherwise we will have a 1.
If we are in the first case the first element of the list will be null.
e.g:

```json
"0": [
    null,
    0,
    null,
    null,
    null
   ]
```

In that example it is right because 0 correspond to 12-26 which is a holiday
(the same for 4: 01-01)
If we are in the second case the first element will be the exchange rate.
e.g:

```json
"2": [
    1.6604,
    1,
    null,
    null,
    null
   ],
```

The other element are null because they doesn't carry any meaning (when we have
"values": [] in the information given. They are null because the information is
in the "id" and "name" at the end of the json output).

It is important to notice that we get this only when &detail=full in the url (we
did this only to understand the output).
In the real application we will use &detail=dataonly. The output will simply be
the first value (null if holiday and a float otherwise). An example is given
at the end of the script.

When the selected date is a weekend, we will likely be given the date till friday
(as in the example, 12-29 and 12-30 are not present). In the case the date is sunday
and friday is a holiday we will get null for the last keys (corresponding to
friday, not sunday). So we will take the exchange rate of thursday.

From the output we take the last day given (last keys of "observations"). If the
value is null we take the previous one. If that is null we take the previous one
and so on.

The ECB API allows to request currencies that are no more used (e.g. HRK removed from
2023-01-01, LVL removed from 2014-01-01 ... ). In that case the index of the observation
dictionary will stop at a certain index (e.g. the idx corresponding to 2013-12-31 for LVL).
If the required date range doesn't include any date where the exchange rate for that
currency is available, nothing is returned. i.e. in the currency list that currency will
not be present. If that is the only required currency a 404 error or an empty content
can be returned by the provider. In that case, this error should be accounted outside
the module that concerns this API.

There’s an edge case, though. Actually, when an exchange rate for a single date is required,
the module using this API require a range of date that start from 7 days before the given
date (becuase, otherwise, for weekends the content would be empty). So, for instance, if
we require the exchange rate for HRK in 2023-01-01 (or 6 days above) we wouldn't get
this date marked as out of range (or raise an empty content error) becuase for the 7 days
before the exchange rates are available and, when a date doesn't exist, the library will
take the preceding days. Those case are ignored since there are few of them and can't be
done easly (how to handle future currencies withdrawal?).

There is another problem that can occour. It happen when asking for the currency ISK.
From 2008 to 2019 the data are not available (unavailable also on the official web
page). So, we choose to ignore this currency since it represent a limited amount of
transactions.

It is set a minimum date, for which the exchange rate will not be required to the API but
will be marked as not available. This date is 2001-01-01.
2001 has been chosen instead of 2000, because some currency were not available in that
date. For example consider BGN, rate are available from 2000-07-19
(see: https://data.ecb.europa.eu/currency-converter). In this case there can
be two things happening when requiring a date below that date:

- If another currency is required for which exchange rate are available past 2000-07-19
  (e.g. USD) the returned date list will start from required starting date and the index
  in the returned observations will start from a bigger value than "0" (the idx
  corresponding to 2000-07-19).
- If the other required currency start from a date above that (or if requiring only BGN),
  the returned date will start from 2000-07-19.

Sometimes (the reason is unknown) some index is missing. Try getting the exchange rate
for RON and PLN at the same time from 2000-02-01 to an higher date (2001-01-01). For RON
the exchange rate for the 63-th index (date:2000-04-21) is missing. This happen also for
dates lower than 2000-01-01. If PLN is removed from the required currencies and
substituted with another currency, e.g. USD, the index reappear (works also by requiring
only RON alone). In this case, we take the value of the previous date since the problem is
with the API provider (anyway this seems to occour only for RON with PLN for very old dates)

Another problem that can occour (with unknown reason) is that sometimes the returned date
aren't sorted. This happen for example when requiring currencies (BGN, USD) (not the whole
available currencies, seems to happen only with BGN requested with few more currencies),
from 2000-07-18 -> 2000-07-21. The returned date list will be orderd in this way:

```json
    {
        "id": "2000-07-19",
        "name": "2000-07-19",
        "start": "2000-07-19T00:00:00.000+00:00",
        "end": "2000-07-19T23:59:59.999+00:00"
    },
    {
        "id": "2000-07-20",
        "name": "2000-07-20",
        "start": "2000-07-20T00:00:00.000+00:00",
        "end": "2000-07-20T23:59:59.999+00:00"
    },
    {
        "id": "2000-07-21",
        "name": "2000-07-21",
        "start": "2000-07-21T00:00:00.000+00:00",
        "end": "2000-07-21T23:59:59.999+00:00"
    },
    {
        "id": "2000-07-14",
        "name": "2000-07-14",
        "start": "2000-07-14T00:00:00.000+00:00",
        "end": "2000-07-14T23:59:59.999+00:00"
    },
    {
        "id": "2000-07-17",
        "name": "2000-07-17",
        "start": "2000-07-17T00:00:00.000+00:00",
        "end": "2000-07-17T23:59:59.999+00:00"
    },
    {
        "id": "2000-07-18",
        "name": "2000-07-18",
        "start": "2000-07-18T00:00:00.000+00:00",
        "end": "2000-07-18T23:59:59.999+00:00"
    }
```

And, for BGN the returned index will be ("0", "1", "2"). But, for USD it is
("3", "4", "5", "0", "1", "2"). Probably the provider returned unordered values becuase
BGN the data are available from 2000-07-19 (first date of the list). So, the keys of the
returned values doesn't match the ascending order of dates, but rather the returned order.
I.e. 2000-07-19 -> "0", ..., 2000-07-14 -> "3". So, it is necessary to sort dates while
moving also those index. This phenomena seems to occour only in special cases and is
rather unlikly to happen.
Another way to get this effect is to fetch for USD and ISK monthly avaraged (M. instead
of D.) in a range 2008-01-01 -> 2020-01-01

The input is the date at which the expenses happen (the date inserted in the database).
With the European Central Banck (ECB) API we get an avarage on that day.

If the date is the current date or it is the day after but closely after 00:00
the output file doesn't contain the required date

The output is ordered with currency in alphabetic order, indipendently on the
order we give to the url.

See: https://data.ecb.europa.eu/help/api/data
for the documentation.
