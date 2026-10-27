#!/usr/bin/env python3
"""
CPSC 473 & 673 - Introduction to Data Mining
Assignment 1: Apriori Algorithm Implementation for Frequent Pattern Mining

This implementation strictly follows the textbook horizontal Apriori algorithm:
  1. Pass 1: Scans the transaction database from file to determine frequent 1-itemsets (L1).
  2. For level k (k >= 2):
     a. Candidate Generation (apriori_gen):
        - Join Step: Joins L_{k-1} with L_{k-1} (itemsets sharing the first k-2 items).
        - Prune Step: Enforces the Apriori downward-closure property (all (k-1)-subsets must be frequent).
     b. Database Scan:
        - Scans the transaction database to count candidate support by testing subset containment.
     c. Filtering:
        - Selects candidates meeting minimum support threshold to form L_k.
  3. Outputs frequent patterns to console and to mining_result_<datasetFileName>.txt.

Usage:
    python apriori.py <dataset_file_path> <minsup>

Examples:
    python apriori.py ./data.txt 50
    python apriori.py ./t25i10d10k.txt 5
    python apriori.py ./retail.txt 2
"""

import sys
import os
import time
import math
from collections import defaultdict
from itertools import combinations


def parse_arguments():
    """
    Parses command-line arguments.
    Expected: python apriori.py <dataset_path> <minsup>
    """
    if len(sys.argv) < 3:
        print("Usage: python apriori.py <dataset_file_path> <minsup>")
        print("Example: python apriori.py ./data.txt 50")
        sys.exit(1)

    dataset_path = sys.argv[1]
    if not os.path.exists(dataset_path):
        print(f"Error: Dataset file '{dataset_path}' not found.")
        sys.exit(1)

    raw_minsup = sys.argv[2].strip()
    try:
        if raw_minsup.endswith('%'):
            minsup_pct = float(raw_minsup[:-1])
        else:
            val = float(raw_minsup)
            # If specified as a ratio <= 1.0 (e.g., 0.05 or 0.50), convert to percentage
            if 0 < val <= 1.0:
                minsup_pct = val * 100.0
            else:
                minsup_pct = val
    except ValueError:
        print(f"Error: Invalid minimum support threshold '{sys.argv[2]}'. Must be a numeric percentage.")
        sys.exit(1)

    return dataset_path, minsup_pct


def stream_raw_transactions(filepath):
    """
    Generator that reads transactions directly from the database file line-by-line.
    Handles standard benchmark dataset formats:
      - Optional first line containing total transaction count
      - Tab-separated format: <tid>\\t<item_count>\\t<space-separated items>
      - Whitespace-separated fallback format
    Yields:
      list of sorted integer items for each transaction.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        first_line = True
        for line in f:
            line = line.strip()
            if not line:
                continue

            parts = line.split('\t')
            # Check if line 1 is only the total transaction count header
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

            items = sorted(int(x) for x in raw_items)
            yield items


def scan_database_for_L1(dataset_path, minsup_pct):
    """
    Pass 1 of Apriori:
    Scans the database file to count frequencies of all 1-items,
    determines the total number of transactions (N) and the minsup transaction count,
    and returns L1 (frequent 1-itemsets).
    """
    item_counts = defaultdict(int)
    num_trans = 0

    for trans in stream_raw_transactions(dataset_path):
        num_trans += 1
        for item in trans:
            item_counts[item] += 1

    minsup_cnt = math.ceil(num_trans * (minsup_pct / 100.0))
    L1 = { (item,): count for item, count in item_counts.items() if count >= minsup_cnt }
    return L1, minsup_cnt, num_trans


def load_filtered_database(dataset_path, L1_items):
    """
    Database reduction: loads the transaction database, retaining only frequent items.
    Transactions with fewer than 2 frequent items are pruned since they cannot contain
    any k-itemset (k >= 2).
    """
    transactions = []
    for trans in stream_raw_transactions(dataset_path):
        filtered = [item for item in trans if item in L1_items]
        if len(filtered) >= 2:
            transactions.append(filtered)
    return transactions


def apriori_gen(current_L, k):
    """
    Candidate Generation Step for Level k (C_k from L_{k-1}):
      1. Join Step: Join two itemsets in L_{k-1} if they share their first (k-2) items.
      2. Prune Step: Check all (k-1)-subsets of the candidate using the Apriori downward
         closure property. If any subset is not in L_{k-1}, prune the candidate.
    Returns:
      candidates: list of candidate tuples of size k.
    """
    # Group itemsets by their length-(k-2) prefix
    prefix_map = defaultdict(list)
    for itemset in sorted(current_L.keys()):
        prefix_map[itemset[:-1]].append(itemset[-1])

    candidates = []
    current_L_set = set(current_L.keys())

    # Join Step
    for prefix, last_items in prefix_map.items():
        n = len(last_items)
        for i in range(n):
            for j in range(i + 1, n):
                cand = prefix + (last_items[i], last_items[j])

                # Prune Step (Apriori Monotonicity Property)
                # Verify that all other (k-1)-subsets exist in current_L
                is_valid = True
                if k > 2:
                    for drop_idx in range(len(cand) - 2):
                        sub = cand[:drop_idx] + cand[drop_idx + 1:]
                        if sub not in current_L_set:
                            is_valid = False
                            break

                if is_valid:
                    candidates.append(cand)

    return candidates


def scan_database_count_candidates(transactions, candidates, k):
    """
    Database Scan Step:
    Scans each transaction in the database and counts occurrences of candidate itemsets.
    Uses efficient subset checking matching textbook Apriori:
      - If transaction length is reasonably bounded, generates k-subsets of transaction and matches against candidate set.
      - Otherwise, directly tests candidate containment within the transaction set.
    """
    cand_counts = defaultdict(int)
    cand_set = set(candidates)

    for trans in transactions:
        if len(trans) < k:
            continue

        n_comb = math.comb(len(trans), k) if len(trans) >= k else 0
        if n_comb > 0 and n_comb <= len(candidates) * 2:
            # Transaction-driven subset counting
            for sub in combinations(trans, k):
                if sub in cand_set:
                    cand_counts[sub] += 1
        else:
            # Candidate-driven subset counting
            trans_set = set(trans)
            for cand in candidates:
                if all(item in trans_set for item in cand):
                    cand_counts[cand] += 1

    return cand_counts


def run_apriori(dataset_path, minsup_pct):
    """
    Full horizontal Apriori algorithm execution:
      - Pass 1: Scan database file to discover frequent 1-itemsets (L1).
      - Passes 2..k:
          Generate C_k via apriori_gen (Join + Prune).
          Scan transaction database to count candidate support.
          Filter candidates meeting minsup to form L_k.
    """
    # Pass 1: Scan database file for L1
    L1, minsup_cnt, num_trans = scan_database_for_L1(dataset_path, minsup_pct)
    if not L1:
        return {}, minsup_cnt, num_trans

    L1_items = set(item[0] for item in L1)

    all_fps = dict(L1)
    current_L = L1
    k = 2

    while current_L:
        # Step 1: Candidate Generation (Join + Prune)
        candidates = apriori_gen(current_L, k)
        if not candidates:
            break

        # Step 2: Database Scan to count candidate support
        
        # Load database filtered to frequent items
        transactions = load_filtered_database(dataset_path, L1_items)

        cand_counts = scan_database_count_candidates(transactions, candidates, k)

        # Step 3: Filter candidates meeting minsup to form L_k
        next_L = { cand: count for cand, count in cand_counts.items() if count >= minsup_cnt }

        all_fps.update(next_L)
        current_L = next_L
        k += 1

    return all_fps, minsup_cnt, num_trans


def save_results(dataset_path, all_fps):
    """
    Saves frequent patterns to mining_result_<datasetFileName>.txt.
    Format:
        Line 1: |FPs| = <count>
        Subsequent lines: item1, item2, ... : count
    """
    base_name = os.path.splitext(os.path.basename(dataset_path))[0]
    out_filename = f"mining_result_{base_name}.txt"

    # Sort itemsets by length ascending, then lexicographically by item IDs
    sorted_fps = sorted(all_fps.items(), key=lambda x: (len(x[0]), x[0]))

    lines = [f"|FPs| = {len(all_fps)}"]
    for itemset, cnt in sorted_fps:
        items_str = ", ".join(str(item) for item in itemset)
        lines.append(f"{items_str} : {cnt}")

    content = "\n".join(lines) + "\n"

    # Save to current working directory
    with open(out_filename, 'w', encoding='utf-8') as f:
        f.write(content)

    # If dataset_path is in another directory, also save there for convenience
    input_dir = os.path.dirname(dataset_path)
    if input_dir and os.path.abspath(input_dir) != os.path.abspath("."):
        alt_path = os.path.join(input_dir, out_filename)
        with open(alt_path, 'w', encoding='utf-8') as f:
            f.write(content)

    return out_filename


def main():
    start_time = time.time()

    dataset_path, minsup_pct = parse_arguments()

    # Mine frequent patterns using textbook Apriori
    all_fps, minsup_cnt, _ = run_apriori(dataset_path, minsup_pct)

    # Save results to file
    save_results(dataset_path, all_fps)

    # Console outputs strictly matching assignment specifications
    total_time = time.time() - start_time
    pct_display = f"{int(minsup_pct)}%" if minsup_pct.is_integer() else f"{minsup_pct:g}%"
    print(f"minsup = {pct_display} = {minsup_cnt}")
    print(f"|FPs| = {len(all_fps)}")
    print(f"Total Runtime: {total_time:.3f} sec")


if __name__ == "__main__":
    main()
