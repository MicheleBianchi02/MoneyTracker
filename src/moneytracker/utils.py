def format_value(value: int | float, format: str) -> str:
    """Change the number formatting given the desired format.

    Parameters
    ----------
        value (int or float) : numerical value to be formatted
        format (str) : code of the format into which transform the number. Possible code are:
            - 'comma_dot' - 1,000.00
            - 'dot_comma' - 1.000,00
            - 'space_comma' - 1 000,00
            - 'space_dot' - 1 000.00
            - 'apo_dot' - 1'000.00
            - 'apo_comma' - 1'000,00
            - 'indian' - 1,00,000.00
            - 'scientific' - 1.00e+3 or 1.00e+0 or 1.0e-1 or 1e-2
            - 'no_separator' - 1000.00

    Returns
    -------
        formatted_str (str) : string with the formatted value
    """

    # Currently it is not required to add the * or - sign in the front
    # if value < 0:
    #     is_negative = True
    #     value = abs(value)
    #
    # elif value > 0:
    #     is_negative = False
    #
    # elif value == 0:
    #     is_negative = False
    #     value = abs(
    #         value
    #     )  # 0 could be passed with a negative sign in the front that has to be removed

    value = round(value, 2)  # Leave only two fractional digits

    str_value = str(value)
    splitted = str_value.split(".")  # '1000.00' -> ['1000', '00']

    # If the value is an integer there will not be any fractional part.
    # Meaning that splitted will have only one item
    if len(splitted) == 1:
        integer = str_value
        fractional = "00"

    elif len(splitted) == 2:
        integer = splitted[0]
        fractional = splitted[1]

    # if value == 1.1 -> 1.10
    if len(fractional) == 1:
        fractional = fractional + "0"

    # Thousands separator

    count = 0
    format_integer = ""

    if format in ["comma_dot", "dot_comma", "space_comma", "space_dot", "apo_dot", "apo_comma"]:
        for letter in integer[::-1]:  # reverse the string
            count = count + 1

            if (
                (count - 1) % 3 != 0 or count == 1
            ):  # when count is 4,7,10... that symbol will increase by one the number of thousands
                format_integer = letter + format_integer

            else:
                if format == "comma_dot":
                    format_integer = letter + "," + format_integer

                elif format == "dot_comma":
                    format_integer = letter + "." + format_integer

                elif format in ["space_comma", "space_dot"]:
                    format_integer = letter + " " + format_integer

                elif format in ["apo_dot", "apo_comma"]:
                    format_integer = letter + "'" + format_integer

    elif format == "indian":  # 1,00,00,00,000 = 1,000,000,000
        for letter in integer[::-1]:  # reverse the string
            count = count + 1

            if count == 4:
                format_integer = letter + "," + format_integer

            # We remove the first 3 symbol. -1 as above
            elif (count - 4) % 2 == 0 and count not in [1, 2, 3, 4, 5]:
                format_integer = letter + "," + format_integer

            else:
                format_integer = letter + format_integer

    # Set the decimal separator
    if format in ["comma_dot", "space_dot", "apo_dot", "indian", "no_separator"]:
        format_str = format_integer + "." + fractional

    elif format in ["dot_comma", "space_comma", "apo_comma"]:
        format_str = format_integer + "," + fractional

    # scientific
    if format == "scientific":
        if integer == "0" and fractional[0] == "0":  # value < 0.10 (0.01 -> 1e-2)
            format_str = fractional[0] + "e" + "-" + "2"

        elif integer == "0" and fractional[0] != "0":  # 0.10 <= value < 1.00 (0.98 -> 9.8e-1)
            format_str = fractional[0] + "." + fractional[1] + "e" + "-" + "1"

        elif len(integer) == 1:
            format_str = integer + "." + fractional + "e" + "+" + "0"

        elif len(integer) == 2:  # value < 100.00 (98.11 -> 9.81e+1)
            format_str = integer[0] + "." + integer[1] + fractional[0] + "e" + "+" + "1"

        elif len(integer) >= 3:  # value >= 100.00 (1234.01 -> 1.23e3)
            length = len(integer)

            format_str = integer[0] + "." + integer[1] + integer[2] + "e" + "+" + f"{length - 1}"

    elif format == "no_separator":
        format_str = integer + "." + fractional

    # # if negative add -, if positive add +
    # if is_negative:
    #     format_str = "-" + format_str
    #
    # else:
    #     if value != 0:  # if value == 0 we leave as "0.00"
    #         format_str = "+" + format_str

    return format_str
