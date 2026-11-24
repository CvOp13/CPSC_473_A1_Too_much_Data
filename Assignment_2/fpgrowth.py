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
    Returns:
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

def count_and_filter_singletons(transactions, minsup):
    """
    Checks if the single items in the provided transaction list 
    meet the minimum support threshold and returns a dictionary of 
    those that do along with its support.
    
    Args:
        transactions: The list of transactions.
        minsup: The minimum support threshold.

    Returns:
        A dictionary of singletons that map to their support.
    """
    # Pairs with a singleton and it's support
    singleton_sups = {}
    for trans in transactions:
        item_list = trans[2]
        for item in item_list:
            if item not in singleton_sups:
                singleton_sups[item] = 1
            else:
                singleton_sups[item] += 1
    
    filtered_singleton_sups = {}
    for (singleton, sup) in singleton_sups.items():
        if sup >= minsup:
            filtered_singleton_sups[singleton] = sup

    return filtered_singleton_sups

class TableItem:
    """
    Represents an item in the header table.
    """
    def __init__(self, item, support):
        self.item = item
        self.support = support
        self.first_node= None 
        self.tail = None

    def __str__(self):
        return f"Header({self.item}: {self.support}) -> {self.first_node}"

    def __repr__(self):
        return str(self)

class TreeNode:
    """
    Represents a node in a FP-tree.
    """
    def __init__(self, item, node_support):
        self.item = item
        self.node_support = node_support
        self.next_node = None
        self.children = []

    def __str__(self):
        return f"Node({self.item}: {self.node_support}) -> {self.next_node}"
    
    def __repr__(self):
        return str(self)

class RootNode:
    """
    Represents a root node in a FP-tree.
    """
    def __init__(self):
        self.children = []
    

def construct_fp_tree_from_transactions(transactions, minsup):
    """
    Constructs an FP-tree from a list of transactions in the form of the output from parse_file.
    Args:
        transactions: The list of transactions.
        minsup: The minimum support threshold.
    """
    filtered_singletons = count_and_filter_singletons(transactions, minsup)
    header_table_map = {}
    for (item, support) in filtered_singletons.items():
        header_table_map[item] = TableItem(item, support)

    root = RootNode()
    for trans in transactions:
        item_list = trans[2]
        current_node = root

        for item in item_list:
            if item in filtered_singletons:

                # Check if item is represented by a child node and get the nodes index if
                # it is
                is_in_children = False 
                item_index = 0
                for child in current_node.children:
                    if item == child.item:
                        is_in_children = True
                        break
                    else:
                        item_index += 1

                if is_in_children:
                    new_current_node = current_node.children[item_index]
                    new_current_node.node_support += 1
                    current_node = new_current_node
                else:
                    new_node = TreeNode(item, 1)
                    header_table_item = header_table_map[item]
                    if header_table_item.first_node == None:
                        header_table_item.first_node = new_node
                        header_table_item.tail = new_node
                    else:
                        end_node = header_table_item.tail
                        end_node.next_node = new_node
                        header_table_item.tail = new_node

                    current_node.children.append(new_node)
                    current_node = new_node
    print_tree(root)
    print(header_table_map)

# for debugging, remove this function later
def print_tree(root):
    print(root.children)
    for node in root.children:
        print_tree(node)
    



def main():
    path, minsup = get_arguments()
    try:
        num_transactions, transactions = parse_file(path)
    except FileNotFoundError:
        print(f"File '{path}' does not exist!")
        sys.exit(1)
    print(num_transactions)
    print(transactions)
    filtered_singletons = count_and_filter_singletons(transactions, minsup)
    print(filtered_singletons)
    construct_fp_tree_from_transactions(transactions, minsup)

if __name__ == "__main__":
    main()
