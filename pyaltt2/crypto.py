# dirty fix for cryptography.Random
import time
try:
    getattr(time, 'clock')
except AttributeError:
    time.clock = time.time

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


def encrypt(raw, key, hmac_key=None, key_is_hash=False, b64=True, bits=256):
    """
    Encrypt bytes with AES-CBC

    Args:
        raw: bytes to encrypt
        key: encryption key
        hmac_key: HMAC key (optional), True or custom key
        key_is_hash: consider encryption key is sha256 hash
        b64: encode result in base64 (default: True)
        bits: key size (128, 192 or 256, default is 256)
    Returns:
        encrypted block + 32-byte HMAC signature (if hmac_key is specified)

    note: if hmac_key is True and key is hash, sha512 sum is required
    """
    from Crypto.Cipher import AES
    from Crypto import Random
    import hashlib
    import hmac
    if isinstance(raw, str):
        raw = raw.encode()
    if hmac_key is True:
        h = key if key_is_hash else hashlib.sha512(
            key.encode() if isinstance(key, str) else key).digest()
        keyhash = h[:bits // 8]
        hmac_key = h[:-32]
    else:
        keyhash = key if key_is_hash else hashlib.sha256(
            key.encode() if isinstance(key, str) else key).digest()[:bits // 8]
    length = 16 - (len(raw) % 16)
    raw += bytes([length]) * length
    iv = Random.new().read(AES.block_size)
    cipher = AES.new(keyhash, AES.MODE_CBC, iv)
    val = iv + cipher.encrypt(raw)
    if hmac_key:
        val += hmac.new(
            hmac_key.encode() if isinstance(hmac_key, str) else hmac_key, val,
            hashlib.sha256).digest()
    if b64:
        import base64
        return base64.b64encode(val).decode()
    else:
        return val


def decrypt(enc, key, hmac_key=None, key_is_hash=False, b64=True, bits=256):
    """
    Decrypt encoded data with AES-CBC

    Args:
        enc: data to decrypt
        key: decryption key
        key_is_hash: consider decryption key is sha256 hash
        hmac_key: HMAC key (optional), True or custom key
        b64: decode data from base64 (default: True)
        bits: key size (128, 192 or 256, default is 256)
    Raises:
        ValueError: if HMAC auth failed

    note: if hmac_key is True and key is hash, sha512 sum is required
    """
    from Crypto.Cipher import AES
    import hashlib
    import hmac
    if b64:
        import base64
        enc = base64.b64decode(enc)
    if hmac_key is True:
        h = key if key_is_hash else hashlib.sha512(
            key.encode() if isinstance(key, str) else key).digest()
        keyhash = h[:bits // 8]
        hmac_key = h[:-32]
    else:
        keyhash = key if key_is_hash else hashlib.sha256(
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


class Rioja:
    """
    Rioja (ˈrjoxa) is a crypto engine, similar to Fernet, but:

    - implements AES-CBC-HMAC up to AES256 (default)
    - more simple to use
    """

    def __init__(self, key, bits=256):
        """
        Args:
            key: encryption key
            bits: key size (128, 192 or 256, default is 256)
        """
        import hashlib
        self.__keyhash = hashlib.sha512(
            key.encode() if isinstance(key, str) else key).digest()
        self.__bits = bits

    def encrypt(self, raw, b64=True):
        """
        Args:
            raw: bytes to encrypt
            b64: encode result in base64 (default: True)
        """
        return encrypt(raw,
                       self.__keyhash,
                       hmac_key=True,
                       key_is_hash=True,
                       b64=b64,
                       bits=self.__bits)

    def decrypt(self, enc, b64=True):
        """
        Args:
            enc: data to decrypt
            b64: decode data from base64 (default: True)
        Raises:
            ValueError: if HMAC auth failed
        """
        return decrypt(enc,
                       self.__keyhash,
                       hmac_key=True,
                       key_is_hash=True,
                       b64=b64,
                       bits=self.__bits)

default_public_key = None
"""
default per-project public key for signature verification
"""

def sign(content, private_key, key_password=None):
    """
    Sign content with RSA key
    Args:
        content: content to sign
        private_key: private RSA (PEM) key
        key_password: key password (optional)
    Returns:
        base64-encoded RSA signature
    """
    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.backends import default_backend
    import hashlib
    import base64

    if not isinstance(content, bytes):
        content = str(content).encode()
    if not isinstance(private_key, bytes):
        private_key = str(private_key).encode()

    privkey = serialization.load_pem_private_key(private_key,
                                                 password=key_password,
                                                 backend=default_backend())

    prehashed = hashlib.sha256(content).digest()

    sig = privkey.sign(
        prehashed,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())

    return base64.b64encode(sig).decode()


def verify_signature(content, signature, public_key=None):
    """
    Verify content with RSA signature

    If public key is not specified, global per-project key is used

    Args:
        content: content to sign
        signature: base64-encoded RSA signature
        public_key: public RSA (PEM) key
    Returns:
        base64-encoded RSA signature
    """
    import hashlib
    import base64
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.backends import default_backend

    if not isinstance(content, bytes):
        content = str(content).encode()
    if public_key is None:
        public_key = default_public_key
    elif not isinstance(public_key, bytes):
        public_key = str(public_key).encode()

    pubkey = serialization.load_pem_public_key(public_key,
                                               backend=default_backend())
    prehashed_msg = hashlib.sha256(content).digest()
    decoded_sig = base64.b64decode(signature)
    pubkey.verify(
        decoded_sig, prehashed_msg,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())
    return True
