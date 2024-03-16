def from_base26(s: str):
    res = 0
    pow = 1
    for i in range(len(s) - 1, -1, -1):
        res += (ord(s[i]) - ord('A') + 1) * pow
        pow *= 26
    return res

def to_base26(n: int):
    res = ''
    while n > 0:
        res += chr(ord('A') + (n % 26 - 1))
        n //= 26
    return res[::-1]