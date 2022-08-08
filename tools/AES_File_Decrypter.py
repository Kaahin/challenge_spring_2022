from hashlib import md5
from Cryptodome.Cipher import AES
from binascii import a2b_base64


def aes_decrypter(file_to_read, file_to_write, key, aes_mode):
    # === Decrypt ===

    # Open the input file and read encrypted data
    with open(file_to_read, "rb") as input_file:
        ct = input_file.read()

    # Create the cipher object
    iv = key[:16]
    cipher_decrypt = AES.new(key, aes_mode, iv=iv)

    # Decrypt data from input file
    encrypted_bytes = a2b_base64(ct)
    decrypted_bytes = cipher_decrypt.decrypt(encrypted_bytes)

    # Write deciphered data to output file
    with open(file_to_write, 'wb') as output_file:
        output_file.write(decrypted_bytes)

    # Print out deciphered data
    print("--------Deciphered Text---------")
    print(decrypted_bytes[:100].decode("utf-8"))


def main():
    # input data
    pw = "asdasd"
    key = md5(pw.encode('latin1')).hexdigest()  # Use a stored / generated key
    print(len(key))
    print(key)
    iv = key[:16]
    key = bytes(key, "latin1")
    iv = bytes(iv, "latin1")
    print(key)
    print(iv)

    aes_mode_decrypt = AES.MODE_OFB

    file_to_read = f"data/%3flevel=4"
    file_to_write = f"data/%3flevel=4_aes"

    aes_decrypter(file_to_read, file_to_write, key, aes_mode_decrypt)


if __name__ == "__main__":
    main()
