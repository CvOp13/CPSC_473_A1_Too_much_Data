#!/usr/bin/env python3
"""
CPSC 473 & 673 - Introduction to Data Mining
Assignment 2: FP-Growth Algorithm Implementation for Frequent Pattern Mining

This implementation follows the canonical FP-growth algorithm (Han, Pei, Yin):
  1. Pass 1 (Scan): Streams the transaction database to count 1-item frequencies,
     determines total transactions (N) and minimum support count, and builds the
     descending frequency list (F-list) of frequent items.
  2. Pass 2 (FP-Tree Construction): Compacts each transaction to frequent items
     sorted in F-list order, aggregates identical projected transactions by
     multiplicity, and inserts them into a compact prefix-tree with O(1) child
     lookups and linked header-table node chains.
  3. Recursive Pattern Growth (Mine):
     - Applies single-prefix-path combinatorial extraction whenever the tree (or
       conditional tree) forms a single linear path.
     - Otherwise traverses header-table items in ascending support order, collects
       conditional pattern bases while simultaneously accumulating local item
       supports, builds pruned conditional FP-trees, and mines recursively.
  4. Outputs frequent patterns to the console and to
     mining_result_<datasetFileName>.txt.

Usage:
    python fpgrowth.py <dataset_file_path> <minsup>

Examples:
    python fpgrowth.py ./data.txt 50
    python fpgrowth.py ./t25i10d10k.txt 5
    python fpgrowth.py ./retail.txt 2
"""

import sys
import os
import time
import math
from collections import defaultdict, Counter
from itertools import combinations


def parse_arguments():
    """
    Parses command-line arguments.
    Expected: python fpgrowth.py <dataset_path> <minsup>
    """
    if len(sys.argv) < 3:
        print("Usage: python fpgrowth.py <dataset_file_path> <minsup>")
        print("Example: python fpgrowth.py ./data.txt 50")
        sys.exit(1)

    dataset_path = sys.argv[1]
    if not os.path.exists(dataset_path):
        print(f"Error: Dataset file '{dataset_path}' not found.")
        sys.exit(1)

    raw_minsup = sys.argv[2].strip()
    try:
        if raw_minsup.endswith("%"):
            minsup_pct = float(raw_minsup[:-1])
        else:
            val = float(raw_minsup)
            # Treat strictly fractional inputs (e.g., 0.50, 0.05) as percentages
            if 0 < val < 1.0:
                minsup_pct = val * 100.0
            else:
                minsup_pct = val
    except ValueError:
        print(
            f"Error: Invalid minimum support threshold '{sys.argv[2]}'. "
            "Must be a numeric percentage."
        )
        sys.exit(1)

    if minsup_pct <= 0 or minsup_pct > 100:
        print("Error: Minimum support percentage must be in (0, 100].")
        sys.exit(1)

    return dataset_path, minsup_pct


def load_transactions_and_counts(filepath):
    """
    Reads the transaction database in a single pass.
    Supports:
      - Optional first line containing total transaction count
      - Tab-separated format: <tid>\\t<item_count>\\t<space-separated items>
      - Whitespace-separated fallback format
    Returns:
      (transactions, item_counts, num_trans)
    """
    transactions = []
    item_counts = defaultdict(int)
    num_trans = 0

    with open(filepath, "r", encoding="utf-8") as f:
        first_line = True
        for line in f:
            line = line.strip()
            if not line:
                continue

            parts = line.split("\t")
            # Skip optional header line containing only transaction count
            if first_line and len(parts) == 1 and parts[0].isdigit():
                first_line = False
                continue
            first_line = False

            if len(parts) >= 3:
                raw_items = parts[2].split()
            elif len(parts) == 2:
                raw_items = parts[1].split()
            else:
                raw_items = parts[0].split()

            # Parse integer items at C speed; deduplicate only if a line repeats an item
            items = list(map(int, raw_items))
            if len(items) > 1 and len(set(items)) != len(items):
                items = list(dict.fromkeys(items))

            num_trans += 1
            for item in items:
                item_counts[item] += 1
            transactions.append(items)

    return transactions, item_counts, num_trans


class FPNode:
    """
    Memory-compact node in an FP-tree using __slots__ and an O(1) child dict.
    """
    __slots__ = ("item", "count", "parent", "children", "node_link")

    def __init__(self, item, count, parent):
        self.item = item
        self.count = count
        self.parent = parent
        self.children = {}
        self.node_link = None


class HeaderEntry:
    """
    Header table entry tracking total item support and the head/tail of its node chain.
    """
    __slots__ = ("support", "head", "tail")

    def __init__(self, support=0):
        self.support = support
        self.head = None
        self.tail = None

    def append_node(self, node):
        if self.head is None:
            self.head = node
            self.tail = node
        else:
            self.tail.node_link = node
            self.tail = node


class FPTree:
    """
    FP-tree storing frequent item prefixes and a linked header table.
    """
    __slots__ = ("root", "header_table", "ordered_items", "single_path")

    def __init__(self):
        self.root = FPNode(None, 0, None)
        self.header_table = {}
        # Items ordered from highest support to lowest support (tie-break: item ID asc)
        self.ordered_items = []
        self.single_path = True

    def insert_transaction(self, items, count=1):
        """
        Inserts an already-ordered transaction (with multiplicity `count`) into the tree.
        """
        current = self.root
        for item in items:
            child = current.children.get(item)
            if child is not None:
                child.count += count
            else:
                if len(current.children) >= 1:
                    self.single_path = False
                child = FPNode(item, count, current)
                current.children[item] = child
                self.header_table[item].append_node(child)
            current = child


def build_initial_fptree(dataset_path, minsup_pct):
    """
    Constructs the initial FP-tree with single-pass file parsing:
      1. Parse transactions and count 1-item frequencies, computing
         minsup_cnt = ceil(N * minsup_pct / 100).
      2. Filter transactions to frequent items, sort by global F-list order,
         aggregate identical projected transactions by multiplicity, and insert
         each unique compacted transaction once into the FP-tree.
    """
    transactions, item_counts, num_trans = load_transactions_and_counts(dataset_path)

    minsup_cnt = math.ceil(num_trans * (minsup_pct / 100.0))

    # Build F-list: sort by (-support, item_id) for deterministic canonical ordering
    frequent_items = [
        (item, cnt) for item, cnt in item_counts.items() if cnt >= minsup_cnt
    ]
    frequent_items.sort(key=lambda x: (-x[1], x[0]))

    if not frequent_items:
        return None, minsup_cnt, num_trans

    rank = {item: idx for idx, (item, _) in enumerate(frequent_items)}

    tree = FPTree()
    tree.ordered_items = [item for item, _ in frequent_items]
    for item, cnt in frequent_items:
        tree.header_table[item] = HeaderEntry(cnt)

    # Aggregate identical compacted transactions before tree insertion
    projected_counts = Counter()
    for trans in transactions:
        filtered = [item for item in trans if item in rank]
        if filtered:
            filtered.sort(key=rank.__getitem__)
            projected_counts[tuple(filtered)] += 1

    for items_tuple, mult in projected_counts.items():
        tree.insert_transaction(items_tuple, mult)

    return tree, minsup_cnt, num_trans


def build_conditional_fptree(pattern_base, minsup_cnt):
    """
    Constructs a conditional FP-tree from a conditional pattern base:
      pattern_base: list of (prefix_items, count) pairs.
    Returns None if no item in the conditional pattern base meets minsup_cnt.
    """
    cond_counts = defaultdict(int)
    for path, cnt in pattern_base:
        for item in path:
            cond_counts[item] += cnt

    frequent_items = [
        (item, cnt) for item, cnt in cond_counts.items() if cnt >= minsup_cnt
    ]
    if not frequent_items:
        return None

    frequent_items.sort(key=lambda x: (-x[1], x[0]))
    rank = {item: idx for idx, (item, _) in enumerate(frequent_items)}

    cond_tree = FPTree()
    cond_tree.ordered_items = [item for item, _ in frequent_items]
    for item, cnt in frequent_items:
        cond_tree.header_table[item] = HeaderEntry(cnt)

    # Aggregate identical filtered conditional paths before inserting
    compacted = Counter()
    for path, cnt in pattern_base:
        filtered = [item for item in path if item in rank]
        if filtered:
            filtered.sort(key=rank.__getitem__)
            compacted[tuple(filtered)] += cnt

    for items_tuple, mult in compacted.items():
        cond_tree.insert_transaction(items_tuple, mult)

    return cond_tree


def extract_single_path_patterns(tree, prefix, all_fps):
    """
    Single-prefix-path optimization:
    When an FP-tree consists of a single linear path from root to leaf,
    every non-empty subset of nodes on the path combines with `prefix` to form
    a frequent itemset whose support equals the minimum node support among the
    selected nodes (the deepest selected node along the path).
    """
    path_nodes = []
    curr = tree.root
    while curr.children:
        # Single path guarantees exactly one child
        curr = next(iter(curr.children.values()))
        path_nodes.append((curr.item, curr.count))

    n = len(path_nodes)
    for r in range(1, n + 1):
        for combo_indices in combinations(range(n), r):
            # Because parent count >= child count along a path, the deepest index
            # in combo_indices determines the exact support of this subset.
            deepest_idx = combo_indices[-1]
            support = path_nodes[deepest_idx][1]
            pattern = tuple(sorted(prefix + tuple(path_nodes[i][0] for i in combo_indices)))
            all_fps[pattern] = support


def mine_fptree(tree, prefix, minsup_cnt, all_fps):
    """
    Recursively mines frequent patterns from `tree` given current `prefix`.
    """
    if tree is None or not tree.ordered_items:
        return

    # Single-path optimization avoids conditional tree construction entirely
    if tree.single_path:
        extract_single_path_patterns(tree, prefix, all_fps)
        return

    # Traverse header table bottom-up (ascending support)
    for item in reversed(tree.ordered_items):
        entry = tree.header_table[item]
        new_prefix = prefix + (item,)
        pattern_key = tuple(sorted(new_prefix))
        all_fps[pattern_key] = entry.support

        # Collect conditional pattern base by walking parent pointers along node links
        cond_pattern_base = []
        node = entry.head
        while node is not None:
            path = []
            parent = node.parent
            while parent is not None and parent.item is not None:
                path.append(parent.item)
                parent = parent.parent
            if path:
                cond_pattern_base.append((path, node.count))
            node = node.node_link

        if cond_pattern_base:
            cond_tree = build_conditional_fptree(cond_pattern_base, minsup_cnt)
            if cond_tree is not None:
                mine_fptree(cond_tree, new_prefix, minsup_cnt, all_fps)


def run_fpgrowth(dataset_path, minsup_pct):
    """
    Executes the full FP-growth pipeline and returns (all_fps, minsup_cnt, num_trans).
    """
    tree, minsup_cnt, num_trans = build_initial_fptree(dataset_path, minsup_pct)
    all_fps = {}
    if tree is not None:
        mine_fptree(tree, (), minsup_cnt, all_fps)
    return all_fps, minsup_cnt, num_trans


def save_results(dataset_path, all_fps):
    """
    Saves discovered frequent patterns to mining_result_<datasetFileName>.txt.
    Format:
        Line 1: |FPs| = <count>
        Subsequent lines: item1, item2, ... : count
    """
    base_name = os.path.splitext(os.path.basename(dataset_path))[0]
    out_filename = f"mining_result_{base_name}.txt"

    # Sort itemsets by length ascending, then numerically by item IDs
    sorted_fps = sorted(all_fps.items(), key=lambda x: (len(x[0]), x[0]))

    lines = [f"|FPs| = {len(all_fps)}"]
    for itemset, cnt in sorted_fps:
        items_str = ", ".join(str(item) for item in itemset)
        lines.append(f"{items_str} : {cnt}")

    content = "\n".join(lines) + "\n"

    with open(out_filename, "w", encoding="utf-8") as f:
        f.write(content)

    # Also write next to input dataset if executed from a different directory
    input_dir = os.path.dirname(dataset_path)
    if input_dir and os.path.abspath(input_dir) != os.path.abspath("."):
        alt_path = os.path.join(input_dir, out_filename)
        with open(alt_path, "w", encoding="utf-8") as f:
            f.write(content)

    return out_filename


def main():
    start_time = time.time()

    dataset_path, minsup_pct = parse_arguments()

    all_fps, minsup_cnt, _ = run_fpgrowth(dataset_path, minsup_pct)

    save_results(dataset_path, all_fps)

    total_time = time.time() - start_time
    pct_display = (
        f"{int(minsup_pct)}%" if minsup_pct.is_integer() else f"{minsup_pct:g}%"
    )
    print(f"minsup = {pct_display} = {minsup_cnt}")
    print(f"|FPs| = {len(all_fps)}")
    print(f"Total Runtime: {total_time:.3f} sec")


if __name__ == "__main__":
    main()
