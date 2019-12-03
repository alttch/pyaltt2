def gen_random_str(length=32):
    """
    Generate random string (letters+numbers)

    Args:
        length: string length (default: 32)
    """
    import string
    import random
    symbols = string.ascii_letters + '0123456789'
    return ''.join(random.choice(symbols) for i in range(length))


def encrypt(raw, key, hmac_key=None, encode=True, bits=256):
    """
    Encrypt bytes with AES-CBC

    Args:
        raw: bytes to encrypt
        key: encryption key
        hmac_key: HMAC key (optional)
        encode: encode result in base64 (default: True)
        bits: key size (128, 192 or 256, default is 256)
    Returns:
        encrypted block + 32-byte HMAC signature (if hmac_key is specified)
    """
    from Crypto.Cipher import AES
    from Crypto import Random
    import hashlib
    import hmac
    keyhash = hashlib.sha256(
        key.encode() if isinstance(key, str) else key).digest()[:bits // 8]
    length = 16 - (len(raw) % 16)
    raw += b'\x00' * (length - 1) + bytes([length])
    iv = Random.new().read(AES.block_size)
    cipher = AES.new(keyhash, AES.MODE_CBC, iv)
    val = iv + cipher.encrypt(raw)
    if hmac_key:
        val += hmac.new(
            hmac_key.encode() if isinstance(hmac_key, str) else hmac_key, val,
            hashlib.sha256).digest()
    if encode:
        import base64
        return base64.b64encode(val).decode()
    else:
        return val


def decrypt(enc, key, hmac_key=None, decode=True, bits=256):
    """
    Decrypt encoded data with AES-CBC

    Args:
        enc: data to decrypt
        key: decryption key
        hmac_key: HMAC key (optional)
        decode: decode data from base64 (default: True)
        bits: key size (128, 192 or 256, default is 256)
    Raises:
        ValueError: if HMAC auth failed
    """
    from Crypto.Cipher import AES
    import hashlib
    import hmac
    if decode:
        import base64
        enc = base64.b64decode(enc)
    keyhash = hashlib.sha256(
        key.encode() if isinstance(key, str) else key).digest()[:bits // 8]
    iv = enc[:16]
    if hmac_key:
        if hmac.new(
                hmac_key.encode() if isinstance(hmac_key, str) else hmac_key,
                enc[:-32], hashlib.sha256).digest() != enc[-32:]:
            raise ValueError('HMAC auth failed')
    cipher = AES.new(keyhash, AES.MODE_CBC, iv)
    data = cipher.decrypt(enc[16:-32 if hmac_key else None])
    return data[:-data[-1]]
