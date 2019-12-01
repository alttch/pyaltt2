def parse_host_port(hp, default_port=0):
    """
    Parse host/port from string

    Doesn't work with IPv6

    Args:
        hp: host/port string to parse
        default_port: default port if no port is specified (default: 0)

    Returns:
        tuple (host, port)
    """
    if hp.find(':') == -1:
        return (hp, default_port)
    else:
        host, port = hp.rsplit(':', 1)
        return (host, int(port))


def netacl_match(ip, acl):
    """
    Check if IP mathches network ACL

    Doesn't work with IPv6

    Args:
        ip: IP address to check
        acl: list of netadd.IPNetwork objects

    Returns:
        True if ACL matches, False if not
    """
    from netaddr import IPAddress
    ipa = IPAddress(ip)
    for a in acl:
        if ipa in a: return True
    return False
