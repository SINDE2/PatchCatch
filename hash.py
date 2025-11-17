import hashlib

def hashing(data):
    encode = data.encode('utf-8')
    hash_data = hashlib.sha256(encode)
    hash_hex = hash_data.hexdigest()

    return hash_hex