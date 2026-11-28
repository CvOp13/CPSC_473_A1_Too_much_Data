# CPSC 473 & 673: Introduction to Data Mining
## Assignment 2: FP-Growth Algorithm for Frequent Pattern Mining

**Team Name:** `too_much_data`  
**Course:** CPSC 473 (Undergraduate) / CPSC 673 (Graduate) — UNBC Department of Computer Science  
**Language:** Python 3 (Tested on Python 3.13)  

---

## 1. Project Overview

This project implements the **FP-Growth (Frequent Pattern Growth)** algorithm for frequent pattern mining as specified in Assignment 2. The program reads transactional databases from `.txt` files (validating each `<tid> <item_count> <items...>` row and treating transactions as deduplicated sets of items), constructs a compressed **FP-tree** ordered by descending item frequency (F-list) without candidate generation, recursively mines frequent itemsets via conditional pattern bases and conditional FP-trees, displays required summary metrics to the console, and writes all discovered frequent patterns to `mining_result_<datasetFileName>.txt` in the current working directory.

Our implementation incorporates single-pass transaction loading, projected transaction multiplicity aggregation, `__slots__`-based nodes with $O(1)$ dictionary child lookups, tail-linked header tables, and **single-prefix-path combinatorial extraction**, achieving up to **9.09× speedup** over the included traditional FP-growth baseline (`--baseline`).

---

## 2. Directory Structure

```text
Assignment_2/
├── fpgrowth.py                                  # Main executable FP-Growth program
├── data.txt                                     # Class sample dataset (4 transactions)
├── 1k5L.txt                                     # 1,000 transactions dataset
├── t25i10d10k.txt                               # 9,976 transactions benchmark
├── retail.txt                                   # 88,162 transactions retail dataset
├── connect.txt                                  # 67,557 dense transactions dataset
├── mining_result_data.txt                       # Ground-truth verified output for data.txt
├── team_info.txt                                # Team member & course details
├── README.md                                    # Compilation and running instructions
└── bonus_mark_documentation_too_much_data.pdf   # Bonus marks report (PDF)
```

*(In the Moodle submission archive `CPSC473_a2_too_much_data.zip`, the implementation is placed inside the `FPgrowth/` directory as specified.)*

---

## 3. Requirements & Environment

- **Python Version:** Python 3.8 or higher (tested on Python 3.13.1).
- **Dependencies:** Standard Python libraries only (`sys`, `os`, `time`, `decimal`, `collections`, `itertools`). **No external packages are required to run `fpgrowth.py`.**

---

## 4. Compilation & Running Instructions

Python is an interpreted language, so no compilation step is necessary.

### Command Syntax
```bash
python fpgrowth.py <dataset_file_path> <minsup> [--ratio] [--baseline]
```

*(If running from the submission archive root where `fpgrowth.py` is inside `FPgrowth/`, run `python FPgrowth/fpgrowth.py <dataset_file_path> <minsup>`.)*

### Parameters & Flags
1. `<dataset_file_path>`: Relative or absolute path to the transaction database file (`.txt`). Each transaction row must follow `<tid> <item_count> <items...>` (whitespace-separated); duplicate item IDs within a transaction are deduplicated.
2. `<minsup>`: Minimum support threshold, parsed with exact `Decimal` arithmetic:
   - **Percentage (default):** Bare numbers and `%`-suffixed values are always interpreted as percentages — e.g., `50` (`50%`), `5` (`5%`), `0.5` (`0.5%`), `0.5%` (`0.5%`), `50.000000000000001%`.
   - **`--ratio` (optional flag):** Interprets a bare numeric threshold as a fractional ratio in `(0, 1]` (e.g., `0.5 --ratio` is treated as `50%`).
   - **`--baseline` (optional flag):** Runs the traditional unoptimized two-pass FP-Growth baseline (list-based children, no transaction aggregation, no single-path shortcut) so readers can directly reproduce the bonus report speedups.

---

## 5. Execution Examples

### Example 1: Sample In-Class Dataset (`data.txt` at 50% minsup)
```bash
python fpgrowth.py ./data.txt 50
```
**Console Output:**
```text
minsup = 50% = 2
|FPs| = 9
Total Runtime: 0.008 sec
```
**Generated File:** `mining_result_data.txt`

### Example 2: Benchmark Dataset (`t25i10d10k.txt` at 5% minsup)
```bash
python fpgrowth.py ./t25i10d10k.txt 5
```
**Console Output:**
```text
minsup = 5% = 499
|FPs| = 142
Total Runtime: 0.272 sec
```
*(Traditional baseline via `python fpgrowth.py ./t25i10d10k.txt 5 --baseline`: `1.529 sec` — **5.62× speedup**).*

### Example 3: Synthetic Dataset (`1k5L.txt` at 0.5% minsup)
```bash
python fpgrowth.py ./1k5L.txt 0.5
```
**Console Output:**
```text
minsup = 0.5% = 5
|FPs| = 460
Total Runtime: 0.036 sec
```

### Example 4: Large Retail Dataset (`retail.txt` at 2% minsup)
```bash
python fpgrowth.py ./retail.txt 2
```
**Console Output:**
```text
minsup = 2% = 1764
|FPs| = 55
Total Runtime: 0.538 sec
```

### Example 5: Dense Connect Dataset (`connect.txt` at 90% minsup)
```bash
python fpgrowth.py ./connect.txt 90
```
**Console Output:**
```text
minsup = 90% = 60802
|FPs| = 27127
Total Runtime: 0.835 sec
```

---

## 6. Output Specifications

### 6.1 Console Output
Strictly adheres to Assignment 2 specifications:
1. **Minimum Support Count:** `minsup = <percentage>% = <count>` (exact `Decimal` ceiling `ceil(num_transactions * minsup / 100)`)
2. **Frequent Patterns Count:** `|FPs| = <total_count>`
3. **Execution Time:** `Total Runtime: <seconds:.3f> sec`

### 6.2 File Output
Discovered frequent itemsets are written to `mining_result_<datasetFileName>.txt` in the current working directory:
- **Line 1:** `|FPs| = <total_count>`
- **Following Lines:** Ordered by itemset length ascending, then numerical item order: `<item1>, <item2>, ... : <support_count>`

---

## 7. Algorithm Architecture & Enhancements

1. **Single-Pass Parsing & Exact Decimal Thresholding:** Streams the database once, validates `<tid> <item_count> <items...>`, deduplicates items per transaction, computes exact `Decimal` `minsup_cnt`, and builds the descending F-list.
2. **Projected Transaction Aggregation:** Filters each transaction to frequent items sorted by F-list rank and aggregates identical projected transactions using multiplicity counts before inserting into the FP-tree.
3. **Memory-Compact FP-Tree (`__slots__` + $O(1)$ Dict Children + Tail-Linked Header Table):** Eliminates per-node Python `__dict__` overhead, replaces linear child-list scans with $O(1)$ hash lookups, and appends header links in $O(1)$ via tail pointers.
4. **Single-Prefix-Path Combinatorial Extraction:** Detects single-path FP-trees and conditional FP-trees in $O(1)$ during insertion and directly enumerates all frequent subsets using the deepest node's support, avoiding recursive conditional tree construction.

Refer to `bonus_mark_documentation_too_much_data.pdf` for detailed justifications and reproducible `--baseline` benchmarks.
