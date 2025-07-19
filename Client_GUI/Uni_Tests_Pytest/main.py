prime_nums = []
for num in range(1, 50):
    for div in range(2, num):
        print(num%div)
        if num % div == 0:
            break
    else:
        prime_nums.append(num)
print(prime_nums)