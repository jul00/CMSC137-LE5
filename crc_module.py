# crc_module.py

def find_xor(a, b):
    """Performs bitwise XOR for strings of bits."""
    result = []
    for i in range(1, len(b)):
        if a[i] == b[i]:
            result.append("0")
        else:
            result.append("1")
    return "".join(result)

def mod2div(dividend, divisor):
    """Performs Modulo-2 division to calculate CRC remainders."""
    pick = len(divisor)
    tmp = dividend[0 : pick]
    
    while pick < len(dividend):
        if tmp[0] == '1':
            tmp = find_xor(divisor, tmp) + dividend[pick]
        else:
            tmp = find_xor('0'*pick, tmp) + dividend[pick]
        pick += 1

    if tmp[0] == '1':
        tmp = find_xor(divisor, tmp)
    else:
        tmp = find_xor('0'*pick, tmp)
        
    return tmp

def encode_data(data_str, key):
    """Pads data and appends the calculated CRC remainder."""
    # Convert string data to binary representation
    bin_data = ''.join(format(ord(c), '08b') for c in data_str)
    
    l_key = len(key)
    appended_data = bin_data + '0' * (l_key - 1)
    remainder = mod2div(appended_data, key)
    
    # Combined binary codeword containing data + checksum
    codeword = bin_data + remainder
    return codeword, bin_data
    