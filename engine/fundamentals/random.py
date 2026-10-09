def randomize_number(input_integer):
    r = input_integer
    r = r ^ (r << 13)
    r = r ^ (r >> 7)
    r = r ^ (r << 17)
    r = r % 1000
    return r


if __name__ == "__main__":
    num = 1
    r_num = randomize_number(num)
    print("Рандомизированное число:", r_num)
