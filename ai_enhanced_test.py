# AI Enhanced Commit Test
# This file will be committed using AI-enhanced commit message
# Created: Wed Dec  3 07:41:40 PM UTC 2025

def fibonacci(n):
    '''Generate Fibonacci sequence up to n'''
    sequence = [0, 1]
    while len(sequence) < n:
        sequence.append(sequence[-1] + sequence[-2])
    return sequence[:n]

# AI will enhance the commit message for this file
print('Fibonacci test:', fibonacci(10))

