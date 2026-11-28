#!/usr/bin/env python3
"""
CPSC 473 & 673 - Introduction to Data Mining
Assignment 2: FP-Growth Algorithm Implementation for Frequent Pattern Mining

This implementation follows the canonical FP-growth algorithm (Han, Pei, Yin):
  1. Pass 1 (Scan): Reads the transaction database, validates each row as
     <tid> <item_count> <items...>, deduplicates items within each transaction,
     determines total transactions (N) and exact Decimal-precision minimum
     support count, and builds the descending frequency list (F-list).
  2. Pass 2 (FP-Tree Construction): Filters transactions to frequent items
     sorted in F-list order, aggregates identical projected transactions by
     multiplicity, and inserts them into a compact prefix-tree with O(1) child
     lookups and tail-linked header-table node chains.
  3. Recursive Pattern Growth (Mine):
     - Applies single-prefix-path combinatorial extraction whenever the tree (or
       conditional tree) forms a single linear path.
     - Otherwise traverses header-table items in ascending support order, collects
       conditional pattern bases while walking parent links, builds pruned
       conditional FP-trees, and mines recursively.
  4. Outputs frequent patterns to the console and to
     mining_result_<datasetFileName>.txt in the current working directory.

Usage:
    python fpgrowth.py <dataset_file_path> <minsup> [--ratio] [--baseline]

Examples:
    python fpgrowth.py ./data.txt 50
    python fpgrowth.py ./1k5L.txt 0.5
    python fpgrowth.py ./t25i10d10k.txt 5
    python fpgrowth.py ./t25i10d10k.txt 5 --baseline
"""

import sys
import os
import time
from collections import defaultdict, Counter
from decimal import Decimal, InvalidOperation, ROUND_CEILING, localcontext
from itertools import combinations


def parse_arguments():
    """
    Parses command-line arguments.
    Expected: python fpgrowth.py <dataset_path> <minsup> [--ratio] [--baseline]

    Bare numbers (e.g., 50 or 0.5) are always treated as percentages (50% or 0.5%)
    unless --ratio is explicitly supplied (e.g., 0.5 --ratio -> 50%).
    """
    positional = []
    use_ratio = False
    use_baseline = False

    for arg in sys.argv[1:]:
        if arg == "--ratio":
            use_ratio = True
        elif arg == "--baseline":
            use_baseline = True
        elif arg.startswith("-"):
            print(f"Error: Unknown flag '{arg}'.")
            print("Usage: python fpgrowth.py <dataset_file_path> <minsup> [--ratio] [--baseline]")
            sys.exit(1)
        else:
            positional.append(arg)

    if len(positional) < 2:
        print("Usage: python fpgrowth.py <dataset_file_path> <minsup> [--ratio] [--baseline]")
        print("Example: python fpgrowth.py ./data.txt 50")
        sys.exit(1)

    dataset_path = positional[0]
    if not os.path.exists(dataset_path):
        print(f"Error: Dataset file '{dataset_path}' not found.")
        sys.exit(1)

    raw_minsup = positional[1].strip()
    has_pct_sign = raw_minsup.endswith("%")
    num_str = raw_minsup[:-1].strip() if has_pct_sign else raw_minsup

    try:
        val = Decimal(num_str)
    except InvalidOperation:
        print(
            f"Error: Invalid minimum support threshold '{positional[1]}'. "
            "Must be a numeric percentage."
        )
        sys.exit(1)

    if not val.is_finite():
        print(f"Error: Invalid minimum support threshold '{positional[1]}'.")
        sys.exit(1)

    if use_ratio and not has_pct_sign:
        minsup_pct = val * Decimal(100)
    else:
        minsup_pct = val

    if minsup_pct <= 0 or minsup_pct > 100:
        print("Error: Minimum support percentage must be in (0, 100].")
        sys.exit(1)

    return dataset_path, minsup_pct, use_baseline


def compute_minsup_count(num_trans, minsup_pct):
    """
    Computes ceil(num_trans * minsup_pct / 100) using exact arbitrary-precision
    decimal arithmetic so boundary thresholds (e.g., 50.000000000000001%) never
    lose precision due to binary floating-point rounding.
    """
    pct_str = format(minsup_pct, "f")
    with localcontext() as ctx:
        ctx.prec = max(60, len(str(num_trans)) + len(pct_str) + 16)
        cutoff = (Decimal(num_trans) * minsup_pct) / Decimal(100)
        return int(cutoff.to_integral_value(rounding=ROUND_CEILING))


def format_minsup_pct(minsup_pct):
    """
    Formats a Decimal percentage cleanly without binary float precision loss.
    """
    s = format(minsup_pct, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return f"{s}%"


def parse_transaction_line(line, line_num):
    """
    Parses and validates a single transaction row in <tid> <item_count> <items...>
    format (whitespace-separated: spaces or tabs). Deduplicates items within the
    transaction so repeated item IDs cannot inflate support.
    """
    tokens = line.split()
    if len(tokens) < 2:
        raise ValueError(
            f"Line {line_num}: expected '<tid> <item_count> <items...>', got {len(tokens)} field(s)."
        )

    try:
        expected_count = int(tokens[1])
    except ValueError as exc:
        raise ValueError(
            f"Line {line_num}: item count '{tokens[1]}' is not a valid integer."
        ) from exc

    raw_items = tokens[2:]
    if len(raw_items) != expected_count:
        raise ValueError(
            f"Line {line_num}: declared item count {expected_count} does not match "
            f"actual item count {len(raw_items)}."
        )

    try:
        items = list(map(int, raw_items))
    except ValueError as exc:
        raise ValueError(f"Line {line_num}: non-integer item ID encountered.") from exc

    # Treat each transaction as a set of items so duplicates cannot double-count
    if len(items) > 1 and len(set(items)) != len(items):
        items = list(dict.fromkeys(items))

    return items


def load_transactions_and_counts(filepath):
    """
    Reads the transaction database in a single pass.
    Supports:
      - Optional first line containing only the total transaction count
      - Whitespace-separated rows: <tid> <item_count> <items...>
    Returns:
      (transactions, item_counts, num_trans)
    """
    transactions = []
    item_counts = defaultdict(int)
    num_trans = 0

    try:
        with open(filepath, "r", encoding="utf-8-sig") as f:
            first_line = True
            for line_num, raw_line in enumerate(f, 1):
                line = raw_line.strip()
                if not line:
                    continue

                tokens = line.split()
                # Skip optional header line containing only the total transaction count
                if first_line and len(tokens) == 1 and tokens[0].isdigit():
                    first_line = False
                    continue
                first_line = False

                items = parse_transaction_line(line, line_num)
                num_trans += 1
                for item in items:
                    item_counts[item] += 1
                transactions.append(items)
    except ValueError as exc:
        print(f"Error parsing dataset '{filepath}': {exc}")
        sys.exit(1)

    return transactions, item_counts, num_trans


def stream_validated_transactions(filepath):
    """
    Streams validated transactions directly from disk (used by --baseline mode
    to faithfully perform two separate disk passes).
    """
    try:
        with open(filepath, "r", encoding="utf-8-sig") as f:
            first_line = True
            for line_num, raw_line in enumerate(f, 1):
                line = raw_line.strip()
                if not line:
                    continue

                tokens = line.split()
                if first_line and len(tokens) == 1 and tokens[0].isdigit():
                    first_line = False
                    continue
                first_line = False

                yield parse_transaction_line(line, line_num)
    except ValueError as exc:
        print(f"Error parsing dataset '{filepath}': {exc}")
        sys.exit(1)


# ==============================================================================
# Optimized FP-Growth Implementation (Default)
# ==============================================================================


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
      1. Parse transactions and count 1-item frequencies, computing exact
         minsup_cnt = ceil(N * minsup_pct / 100).
      2. Filter transactions to frequent items, sort by global F-list order,
         aggregate identical projected transactions by multiplicity, and insert
         each unique compacted transaction once into the FP-tree.
    """
    transactions, item_counts, num_trans = load_transactions_and_counts(dataset_path)
    minsup_cnt = compute_minsup_count(num_trans, minsup_pct)

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
        curr = next(iter(curr.children.values()))
        path_nodes.append((curr.item, curr.count))

    n = len(path_nodes)
    for r in range(1, n + 1):
        for combo_indices in combinations(range(n), r):
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
    Executes the optimized FP-growth pipeline and returns (all_fps, minsup_cnt, num_trans).
    """
    tree, minsup_cnt, num_trans = build_initial_fptree(dataset_path, minsup_pct)
    all_fps = {}
    if tree is not None:
        mine_fptree(tree, (), minsup_cnt, all_fps)
    return all_fps, minsup_cnt, num_trans


# ==============================================================================
# Traditional Baseline FP-Growth Implementation (--baseline)
# ==============================================================================


class BaselineNode:
    """
    Traditional FP-tree node storing children in a linear list without __slots__.
    """

    def __init__(self, item, count, parent):
        self.item = item
        self.count = count
        self.parent = parent
        self.children = []
        self.node_link = None


def build_baseline_tree(item_sequences, counts, minsup_cnt):
    """
    Constructs a traditional FP-tree without transaction aggregation,
    dict children, or tail pointers.
    """
    item_counts = defaultdict(int)
    for seq, mult in zip(item_sequences, counts):
        for item in seq:
            item_counts[item] += mult

    freq = [(item, cnt) for item, cnt in item_counts.items() if cnt >= minsup_cnt]
    if not freq:
        return None, {}

    freq.sort(key=lambda x: (-x[1], x[0]))
    rank = {item: idx for idx, (item, _) in enumerate(freq)}
    header = {item: [cnt, None] for item, cnt in freq}

    root = BaselineNode(None, 0, None)
    for seq, mult in zip(item_sequences, counts):
        filtered = [item for item in seq if item in rank]
        if not filtered:
            continue
        filtered.sort(key=rank.__getitem__)
        curr = root
        for item in filtered:
            found = None
            for child in curr.children:
                if child.item == item:
                    found = child
                    break
            if found is not None:
                found.count += mult
                curr = found
            else:
                new_node = BaselineNode(item, mult, curr)
                curr.children.append(new_node)
                if header[item][1] is None:
                    header[item][1] = new_node
                else:
                    link = header[item][1]
                    while link.node_link is not None:
                        link = link.node_link
                    link.node_link = new_node
                curr = new_node

    return root, header


def mine_baseline_tree(header, prefix, minsup_cnt, all_fps):
    """
    Traditional recursive FP-growth mining without single-prefix-path shortcut.
    """
    ordered = sorted(header.items(), key=lambda x: (x[1][0], -x[0]))
    for item, (support, head) in ordered:
        new_prefix = prefix + (item,)
        all_fps[tuple(sorted(new_prefix))] = support

        cond_paths = []
        cond_counts = []
        node = head
        while node is not None:
            path = []
            parent = node.parent
            while parent is not None and parent.item is not None:
                path.append(parent.item)
                parent = parent.parent
            if path:
                cond_paths.append(path)
                cond_counts.append(node.count)
            node = node.node_link

        if cond_paths:
            _, cond_header = build_baseline_tree(cond_paths, cond_counts, minsup_cnt)
            if cond_header:
                mine_baseline_tree(cond_header, new_prefix, minsup_cnt, all_fps)


def run_baseline_fpgrowth(dataset_path, minsup_pct):
    """
    Executes traditional two-pass FP-growth without optimizations (--baseline).
    """
    # Pass 1: count 1-item supports and total transactions
    item_counts = defaultdict(int)
    num_trans = 0
    for trans in stream_validated_transactions(dataset_path):
        num_trans += 1
        for item in trans:
            item_counts[item] += 1

    minsup_cnt = compute_minsup_count(num_trans, minsup_pct)
    freq = [(item, cnt) for item, cnt in item_counts.items() if cnt >= minsup_cnt]
    if not freq:
        return {}, minsup_cnt, num_trans

    freq.sort(key=lambda x: (-x[1], x[0]))
    rank = {item: idx for idx, (item, _) in enumerate(freq)}
    header = {item: [cnt, None] for item, cnt in freq}

    # Pass 2: re-read from disk and insert each transaction individually
    root = BaselineNode(None, 0, None)
    for trans in stream_validated_transactions(dataset_path):
        filtered = [item for item in trans if item in rank]
        if not filtered:
            continue
        filtered.sort(key=rank.__getitem__)
        curr = root
        for item in filtered:
            found = None
            for child in curr.children:
                if child.item == item:
                    found = child
                    break
            if found is not None:
                found.count += 1
                curr = found
            else:
                new_node = BaselineNode(item, 1, curr)
                curr.children.append(new_node)
                if header[item][1] is None:
                    header[item][1] = new_node
                else:
                    link = header[item][1]
                    while link.node_link is not None:
                        link = link.node_link
                    link.node_link = new_node
                curr = new_node

    all_fps = {}
    mine_baseline_tree(header, (), minsup_cnt, all_fps)
    return all_fps, minsup_cnt, num_trans


# ==============================================================================
# Output & CLI Entry Point
# ==============================================================================


def save_results(dataset_path, all_fps):
    """
    Saves discovered frequent patterns to mining_result_<datasetFileName>.txt
    in the current working directory.
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

    return out_filename


def main():
    start_time = time.time()

    dataset_path, minsup_pct, use_baseline = parse_arguments()

    if use_baseline:
        all_fps, minsup_cnt, _ = run_baseline_fpgrowth(dataset_path, minsup_pct)
    else:
        all_fps, minsup_cnt, _ = run_fpgrowth(dataset_path, minsup_pct)

    save_results(dataset_path, all_fps)

    total_time = time.time() - start_time
    pct_display = format_minsup_pct(minsup_pct)
    print(f"minsup = {pct_display} = {minsup_cnt}")
    print(f"|FPs| = {len(all_fps)}")
    print(f"Total Runtime: {total_time:.3f} sec")


if __name__ == "__main__":
    main()
