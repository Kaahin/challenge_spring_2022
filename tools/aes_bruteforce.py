from string import ascii_lowercase
from hashlib import md5
from multiprocessing import Process, Value
from Cryptodome.Cipher import AES
from pwn import xor
from binascii import a2b_base64


def pw_to_md5_decrypter(pw):
    key = md5(pw.encode('latin1')).hexdigest()
    iv = key[0:16]
    key = bytes(key, 'latin1')
    iv = bytes(iv, 'latin1')
    aes_mode = AES.MODE_ECB

    ecb_cipher = AES.new(key, aes_mode)
    keystream = ecb_cipher.encrypt(iv)
    return keystream


def generate_text(n, chars):
    if n == 0:
        yield ""
    else:
        pw_list = generate_text(n - 1, chars)
        for pw in pw_list:
            for c in chars:
                yield pw + c


def single_process(initial_text, chars, length, keystream_comp, flag):
    for i in range(length, length + 1):
        for text in generate_text(i, chars):
            combined_text = initial_text + text
            keystream_guess = pw_to_md5_decrypter(combined_text)

            if flag.value == 1:
                break
            if keystream_comp[:16] == keystream_guess[:16]:
                flag.value = 1
                print(f"The password is {combined_text}")
                break


def main():

    with open("data/%3flevel=4", "rb") as f:
        ct_raw_list = f.read()

    with open("data/%3flevel=0", "rb") as f:
        pt = f.read()

    ct_raw = ct_raw_list

    ct = a2b_base64(ct_raw)

    p0 = pt[:32]
    c0 = ct[:32]

    keystream_comp = xor(p0, c0)
    print(p0, '\n', c0, '\n', keystream_comp)

    chars = ascii_lowercase
    length = 5
    processes = []
    flag = Value("i", 0)

    for c in chars:
        processes.append(Process(target=single_process, args=(
            c, chars, length, keystream_comp, flag)))
    for process in processes:
        process.start()
    for process in processes:
        process.join()


if __name__ == "__main__":
    import cProfile
    name = "output.dat"
    cProfile.run('main()', name)

    import pstats
    from pstats import SortKey

    with open("profiler\output_time.txt", "w") as f:
        p = pstats.Stats(name, stream=f)
        p.sort_stats(SortKey.TIME).print_stats()

    with open("profiler\output_call.txt", "w") as f:
        p = pstats.Stats(name, stream=f)
        p.sort_stats(SortKey.CALLS).print_stats()
