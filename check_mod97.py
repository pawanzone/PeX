def mod97(iban):
    clean = iban.replace(" ", "").upper()
    rearranged = clean[4:] + clean[:4]
    num_str = ""
    for ch in rearranged:
        if ch.isdigit():
            num_str += ch
        elif ch.isalpha():
            num_str += str(ord(ch) - 55)
    return int(num_str) % 97

print("GB82WEST12345698765432 mod 97:", mod97("GB82WEST12345698765432"))
print("GB82WEST12345698765431 mod 97:", mod97("GB82WEST12345698765431"))
print("GB00WEST12345698765432 mod 97:", mod97("GB00WEST12345698765432"))
# Real standard valid UK IBAN: GB29NWBK60161331926819
print("GB29NWBK60161331926819 mod 97:", mod97("GB29NWBK60161331926819"))
