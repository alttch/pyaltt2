def merge_dict(*args, add_keys=True):
    """
    Safely merge two dictionaries

    Args:
        dct0...n: dicts to merge
        add_keys: merge dict keys (default: True)
    Returns:
        merged dict
    """
    if len(args) < 1: return None
    dct = args[0].copy()
    from collections.abc import Mapping
    for merged in args[1:]:
        if not add_keys:
            merged = {
                k: merged[k] for k in set(dct).intersection(set(merged))
            }

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
