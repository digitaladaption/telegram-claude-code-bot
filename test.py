
def add(a, b):
    return a + b

def multiply(a, b):
    return a * b

# This function has a bug!
def calculate_total(items):
    total = 0
    for item in items:
        total = item  # Bug: should be total += item
    return total
