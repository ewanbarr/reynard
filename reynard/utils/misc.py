def is_power_of_two(n):
    """
    @brief  Test if number is a power of two

    @return True|False
    """
    return n != 0 and ((n & (n - 1)) == 0)

def next_power_of_two(n):
    """
    @brief  Round a number up to the next power of two
    """
    return 2**(n-1).bit_length()