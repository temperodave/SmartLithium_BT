from contextlib import contextmanager
from ctypes import POINTER, cdll, c_char_p, c_void_p, c_int, create_string_buffer, byref
from sys import platform

# Uses a _little_ endian CTR counter, which OpenSSL doesn't directly support.
# Could be used to decrypt AES-encrypted ZIP files
def decrypt_aes_128_ctr_little_endian(
    key, init_val, ciphertext_chunks,
    get_libcrypto=lambda: cdll.LoadLibrary({'linux': 'libcrypto.so', 'darwin': 'libcrypto.dylib'}[platform])
):
    def non_null(result, func, args):
        if result == 0:
            raise Exception('Null value returned')
        return result

    def ensure_1(result, func, args):
        if result != 1:
            raise Exception(f'Result {result}')
        return result

    libcrypto = get_libcrypto()
    libcrypto.EVP_CIPHER_CTX_new.restype = c_void_p
    libcrypto.EVP_CIPHER_CTX_new.errcheck = non_null
    libcrypto.EVP_CIPHER_CTX_free.argtypes = (c_void_p,)

    libcrypto.EVP_DecryptInit_ex.argtypes = (c_void_p, c_void_p, c_void_p, c_char_p, c_char_p)
    libcrypto.EVP_DecryptInit_ex.errcheck = ensure_1
    libcrypto.EVP_DecryptUpdate.argtypes = (c_void_p, c_char_p, POINTER(c_int), c_char_p, c_int)
    libcrypto.EVP_DecryptUpdate.errcheck = ensure_1

    libcrypto.EVP_aes_128_ctr.restype = c_void_p

    @contextmanager
    def cipher_context():
        ctx = libcrypto.EVP_CIPHER_CTX_new()
        try:
            yield ctx
        finally:
            libcrypto.EVP_CIPHER_CTX_free(ctx)

    def in_fixed_size_chunks(chunks, size):
        chunk = b''
        offset = 0
        it = iter(chunks)

        def get(size):
            nonlocal chunk, offset

            while size:
                if not chunk:
                    try:
                        chunk = next(it)
                    except StopIteration:
                        return
                to_yield = min(size, len(chunk) - offset)
                yield chunk[offset:offset + to_yield]
                offset = (offset + to_yield) % len(chunk)
                chunk = chunk if offset else b''
                size -= to_yield

        while True:
            fixed_size_chunk = b''.join(get(size))
            if fixed_size_chunk:
                yield fixed_size_chunk
            else:
                break

    def decrypted_chunks(fixed_size_chunks):
        for j, chunk in enumerate(fixed_size_chunks):
            with cipher_context() as ctx:
                plaintext = create_string_buffer(16)
                plaintext_len = c_int()
#                print('Decryptor key ',key.hex(), ' IV ',(j + 1 + init_val).to_bytes(16, byteorder='little').hex())
                libcrypto.EVP_DecryptInit_ex(ctx, libcrypto.EVP_aes_128_ctr(), None, key, (j + 1 + init_val).to_bytes(16, byteorder='little'))
                libcrypto.EVP_DecryptUpdate(ctx, plaintext, byref(plaintext_len), chunk, len(chunk))
                yield plaintext.raw[:plaintext_len.value]

    fixed_size_chunks = in_fixed_size_chunks(ciphertext_chunks, 16)
    decrypted_chunks = decrypted_chunks(fixed_size_chunks)
    yield from decrypted_chunks
