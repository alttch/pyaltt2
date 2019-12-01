def gen_random_str(length=64):
    """
    Generate random string (letters+numbers)

    Args:
        length: string length (default: 64)
    """
    import string
    import random
    symbols = string.ascii_letters + '0123456789'
    return ''.join(random.choice(symbols) for i in range(length))


def _pad_key(key):
    if len(key) < 16:
        return key.ljust(16)
    elif len(key) < 24:
        return key.ljust(24)
    elif len(key) < 32:
        return key.ljust(32)
    else:
        return key[:32]


def encrypt(raw, key, encode=True):
    """
    Encrypt bytes with AES-256-CBC

    Args:
        raw: bytes to encrypt
        key: encryption key (32 bytes max, string)
        encode: encode result in base64 (default: True)
    """
    from Crypto.Cipher import AES
    from Crypto import Random
    length = 16 - (len(raw) % 16)
    raw += bytes([length]) * length
    iv = Random.new().read(AES.block_size)
    cipher = AES.new(_pad_key(key), AES.MODE_CBC, iv)
    val = iv + cipher.encrypt(raw)
    if encode:
        import base64
        return base64.b64encode(val).decode()
    else:
        return val


def decrypt(enc, key, decode=True):
    """
    Decrypt encoded data with AES-256-CBC

    Args:
        enc: data to decrypt
        key: decryption key
        decode: decode data from base64 (default: True)
    """
    from Crypto.Cipher import AES
    if decode:
        import base64
        enc = base64.b64decode(enc)
    iv = enc[:16]
    cipher = AES.new(_pad_key(key), AES.MODE_CBC, iv)
    data = cipher.decrypt(enc[16:])
    return data[:-data[-1]]
