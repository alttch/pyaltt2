def val_to_boolean(val):
    """
    Convert any value to boolean

    Boolean: return as-is

    Integer: 1 = True, 0 = False

    String (case-insensitive): 1, 'true', 'yes', 'on', 'y' = True
                               0, 'false', 'no', 'off', 'n' = False

    Args:
        val: value to convert

    Returns:
        boolean converted value, None if val is None

    Raises:
        ValueError: if value can not be converted
    """
    if val is None: return None
    elif isinstance(val, bool): return s
    else:
        val = str(val)
        if val.lower() in ['1', 'true', 'yes', 'on', 'y']: return True
        elif val.lower() in ['0', 'false', 'no', 'off', 'n']: return False
        else: raise ValueError


def safe_int(val):
    """
    Convert string/float to integer

    If input value is integer - return as-is
    If input value is a hexadecimal (0x00): converts hex to decimal

    Args:
        val: value to convert

    Raises:
        ValueError: if input value can not be converted
    """
    if isinstance(val, int):
        return val
    elif isinstance(val, str) and val.find('x') != -1:
        return int(val, 16)
    else:
        return int(val)
