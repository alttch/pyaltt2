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


def encrypt(raw, key, encode=True, bits=256):
    """
    Encrypt bytes with AES-CBC

    Args:
        raw: bytes to encrypt
        key: encryption key
        encode: encode result in base64 (default: True)
        bits: key size (128, 192 or 256, default is 256)
    """
    from Crypto.Cipher import AES
    from Crypto import Random
    import hashlib
    keyhash = hashlib.sha256(
        key.encode() if isinstance(key, str) else key).digest()[:bits // 8]
    length = 16 - (len(raw) % 16)
    raw += bytes([length]) * length
    iv = Random.new().read(AES.block_size)
    cipher = AES.new(keyhash, AES.MODE_CBC, iv)
    val = iv + cipher.encrypt(raw)
    if encode:
        import base64
        return base64.b64encode(val).decode()
    else:
        return val


def decrypt(enc, key, decode=True, bits=256):
    """
    Decrypt encoded data with AES-CBC

    Args:
        enc: data to decrypt
        key: decryption key
        decode: decode data from base64 (default: True)
        bits: key size (128, 192 or 256, default is 256)
    """
    from Crypto.Cipher import AES
    import hashlib
    if decode:
        import base64
        enc = base64.b64decode(enc)
    keyhash = hashlib.sha256(
        key.encode() if isinstance(key, str) else key).digest()[:bits // 8]
    iv = enc[:16]
    cipher = AES.new(keyhash, AES.MODE_CBC, iv)
    data = cipher.decrypt(enc[16:])
    return data[:-data[-1]]
