#!/bin/python3

import sys

def get_arguments():
    """
    Gets the arguments from the command line.

    Returns:
        A tuple of the form (path, minsup) which are parsed from the arguments
    """
    args = sys.argv
    MIN_ARG_LENGTH = 3
    if len(args) < MIN_ARG_LENGTH:
        print("Usage: fpgrowth.py <path> <minsup as a num>")
        print("Ex: fpgrowth.py mining_data.txt 10")
        sys.exit(1)

    PATH_POSITION = 1
    MINSUP_POSITION = 2
    path = args[PATH_POSITION]
    try:
        minsup = int(args[MINSUP_POSITION])
    except ValueError:
        print("Error: minsup must be an integer!")
        sys.exit(1)

    return (path, minsup)

def parse_file(path):
    """
    Parses the file to mine at the provided path. It returns a list of tuples with each 
    tuple representing a transaction of the form (tid, num_items, [items])

    Args:
        path: The path to the file to mine.
    Return:
        A tuple with the first item being a transaction count and the second item being
        a list of tuples with each tuple representing a transaction.
    """
    with open(path, "r") as file:
        is_first_line = True
        num_transactions = 0
        transactions = []
        for line in file:
            if (is_first_line):
                num_transactions = int(line)
                is_first_line = False
            else:
                split_line = line.split()
                trans_id = int(split_line[0])
                num_items = int(split_line[1])
                items = [int(i) for i in split_line[2:]]
                transactions.append((trans_id, num_items, items))
        return (num_transactions, transactions)

def construct_fp_tree_from_transactions(transactions):
    """
    Constructs an FP-tree from a list of transactions in the form of the output from parse_file.
    """


def main():
    path, minsup = get_arguments()
    try:
        num_transactions, transactions = parse_file(path)
    except FileNotFoundError:
        print(f"File '{path}' does not exist!")
        sys.exit(1)
    print(num_transactions)
    print(transactions)

if __name__ == "__main__":
    main()
