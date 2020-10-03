import os

from django.conf import settings
from django.test import TestCase

from teslarent.utils.crypt import encrypt, decrypt


class CryptCase(TestCase):
    def setUp(self):
        pass

    def test_crypt(self):
        salt = os.urandom(8).hex()  # 64-bit salt
        iv = os.urandom(16).hex()  # 128-bit IV
        message = "The answer is yes"
        ciphertext = encrypt(message, settings.SECRET_KEY, salt, iv)
        orig_message = decrypt(ciphertext, settings.SECRET_KEY, salt, iv)
        self.assertEqual(message, orig_message)
