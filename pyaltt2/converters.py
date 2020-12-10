def merge_dict(*args, add_keys=True):
    """
    Safely merge two dictionaries

    Args:
        dct0...n: dicts to merge
        add_keys: merge dict keys (default: True)
    Returns:
        merged dict
    """
    if len(args) < 1:
        return None
    dct = args[0].copy()
    from collections.abc import Mapping
    for merged in args[1:]:
        if not add_keys:
            merged = {k: merged[k] for k in set(dct).intersection(set(merged))}

        for k, v in merged.items():
            if isinstance(dct.get(k), dict) and isinstance(v, Mapping):
                dct[k] = merge_dict(dct[k], v, add_keys=add_keys)
            else:
                if v is None:
                    if not k in dct:
                        dct[k] = None
                else:
                    dct[k] = v
    return dct


def val_to_boolean(val):
    """
    Convert any value to boolean

    Boolean: return as-is

    - Integer: 1 = True, 0 = False
    - Strings (case-insensitive): '1', 'true', 't', 'yes', 'on', 'y' = True
    - '0', 'false', 'f', 'no', 'off', 'n' = False

    Args:
        val: value to convert

    Returns:
        boolean converted value, None if val is None

    Raises:
        ValueError: if value can not be converted
    """
    if val is None:
        return None
    elif isinstance(val, bool):
        return val
    else:
        val = str(val)
        if val.lower() in ['1', 't', 'true', 'yes', 'on', 'y']:
            return True
        elif val.lower() in ['0', 'f', 'false', 'no', 'off', 'n']:
            return False
        else:
            raise ValueError


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
    elif isinstance(val, str):
        if 'x' in val:
            return int(val, 16)
        elif 'b' in val:
            return int(val, 2)
        elif 'o' in val:
            return int(val, 8)
    return int(val)


def parse_date(val=None, return_timestamp=True, ms=False):
    """
    Parse date from string or float/integer

    Input date can be either timestamp or date-time string

    If input value is integer and greater than 3000, it's considered as a
    timestamp, otherwise - as a year

    Args:
        val: value to parse
        return_timestamp: return UNIX timestamp (default) or datetime object
        ms: parse date from milliseconds

    Returns:
        UNIX timestamp (float) or datetime object. If input value is None,
        returns current date/time
    """
    import datetime
    import time
    if val is None:
        return time.time() if return_timestamp else datetime.datetime.now()
    if isinstance(val, datetime.datetime):
        dt = val
    else:
        try:
            val = float(val)
            if ms:
                val /= 1000
            if val > 3000:
                return val if return_timestamp else \
                        datetime.datetime.fromtimestamp(val)
            else:
                val = int(val)
        except:
            pass
        import dateutil.parser
        dt = dateutil.parser.parse(str(val))
    return dt.timestamp() if return_timestamp else dt


def parse_number(val):
    """
    Tries to parse number from any value

    Valid values are:

    - any float / integer
    - 123.45
    - 123 456.899
    - 123,456.899
    - 123 456,899
    - 123.456,82

    Args:
        val: value to parse
    Returns:
        val as-is if val is integer, float or None, otherwise parsed value
    Raises:
        ValueError: if input val can not be parsed
    """
    if isinstance(val, int) or isinstance(val, float) or val is None:
        return val
    if not isinstance(val, str):
        raise ValueError(val)
    else:
        val = val.strip()
    try:
        return float(val)
    except:
        pass
    spaces = val.count(' ')
    commas = val.count(',')
    dots = val.count('.')
    if spaces > 0:
        return float(val.replace(' ', '').replace(',', '.'))
    elif commas > 1:
        return float(val.replace(',', ''))
    elif commas == 1 and commas <= dots:
        if val.find(',') < val.find('.'):
            return float(val.replace(',', ''))
        else:
            return float(val.replace('.', '').replace(',', '.'))
    else:
        return float(val.replace(',', '.'))


def mq_topic_match(topic, mask):
    """
    Checks if topic matches mqtt-style mask

    Args:
        topic: topic (string)
        mask: mask to check

    Returns:
        True if matches, False if don't
    """
    if topic == mask:
        return True
    else:
        ms = mask.split('/')
        ts = topic.split('/')
        lts = len(ts)
    for i, s in enumerate(ms):
        if s == '#':
            return i < lts
        elif i >= lts or (s != '+' and s != ts[i]):
            return False
    return i == lts - 1
