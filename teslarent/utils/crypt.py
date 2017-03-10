from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2


BS = 16
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS)
unpad = lambda s: s[0:-s[-1]]


def encrypt(secret, password, salt, iv):
    key = PBKDF2(password, bytes.fromhex(salt), dkLen=32)  # 256-bit key
    cipher = AES.new(key, AES.MODE_CBC, bytes.fromhex(iv))
    return cipher.encrypt(pad(secret)).hex()


def decrypt(ciphertext, password, salt, iv):
    key = PBKDF2(password, bytes.fromhex(salt), dkLen=32)  # 256-bit key
    cipher = AES.new(key, AES.MODE_CBC, bytes.fromhex(iv))
    return unpad(
        cipher.decrypt(bytes.fromhex(ciphertext))
    ).decode('utf-8')
