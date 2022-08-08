from binascii import unhexlify


file_to_read = f"data\%3flevel=1"

with open(file_to_read, "rb") as input_file:
    ct = input_file.read()

print(ct[:20])

pt = unhexlify(ct)

print(pt[:20])

file_to_write = f"data\%3flevel=1_base16"

with open(file_to_write, "wb") as output_file:
    output_file.write(pt)
