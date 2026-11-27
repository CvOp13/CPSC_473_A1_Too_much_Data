# CPSC 473 & 673: Introduction to Data Mining
## Assignment 2: FP-Growth Algorithm for Frequent Pattern Mining

**Team Name:** `too_much_data`  
**Language:** Python 3 (Tested on Python 3.13)  

---

## 1. Project Overview

This project implements the **FP-Growth (Frequent Pattern Growth)** algorithm for frequent pattern mining as specified in Assignment 2. The program reads transactional databases from `.txt` files, constructs a compressed **FP-tree** ordered by descending item frequency (F-list) without candidate generation, recursively mines frequent itemsets via conditional pattern bases and conditional FP-trees, displays required summary metrics to the console, and writes all discovered frequent patterns to `mining_result_<datasetFileName>.txt`.

Our implementation incorporates single-pass transaction loading, projected transaction multiplicity aggregation, `__slots__`-based nodes with $O(1)$ dictionary child lookups, tail-linked header tables, and **single-prefix-path combinatorial extraction**, achieving up to **4.5× speedup** over a traditional list-based FP-growth implementation and **over 55× speedup** on dense datasets (`connect.txt` at 95% minsup: 1.24s vs 68.57s for Apriori).

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
- **Dependencies:** Standard Python libraries only (`sys`, `os`, `time`, `math`, `collections`, `itertools`). **No external packages are required to run `fpgrowth.py`.**

---

## 4. Compilation & Running Instructions

Python is an interpreted language, so no compilation step is necessary.

### Command Syntax
```bash
python fpgrowth.py <dataset_file_path> <minsup>
```

*(If running from the submission archive root where `fpgrowth.py` is inside `FPgrowth/`, run `python FPgrowth/fpgrowth.py <dataset_file_path> <minsup>`.)*

### Parameters
1. `<dataset_file_path>`: Relative or absolute path to the transaction database file (`.txt`).
2. `<minsup>`: Minimum support threshold percentage. Supports:
   - **Integer / numeric percentage:** e.g., `50` (50%), `5` (5%), `0.5` (treated as 50%; use `0.5%` for half a percent).
   - **Percentage string:** e.g., `50%`, `5%`, `0.5%`.

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
Total Runtime: 0.002 sec
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
Total Runtime: 0.373 sec
```
**Generated File:** `mining_result_t25i10d10k.txt`

### Example 3: Synthetic Dataset (`1k5L.txt` at 1% minsup)
```bash
python fpgrowth.py ./1k5L.txt 1
```
**Console Output:**
```text
minsup = 1% = 10
|FPs| = 213
Total Runtime: 0.014 sec
```

### Example 4: Large Retail Dataset (`retail.txt` at 2% minsup)
```bash
python fpgrowth.py ./retail.txt 2
```
**Console Output:**
```text
minsup = 2% = 1764
|FPs| = 55
Total Runtime: 0.434 sec
```

### Example 5: Dense Connect Dataset (`connect.txt` at 90% minsup)
```bash
python fpgrowth.py ./connect.txt 90
```
**Console Output:**
```text
minsup = 90% = 60802
|FPs| = 27127
Total Runtime: 1.217 sec
```

---

## 6. Output Specifications

### 6.1 Console Output
Strictly adheres to Assignment 2 specifications:
1. **Minimum Support Count:** `minsup = <percentage>% = <count>` (where `count = ceil(num_transactions * minsup / 100)`)
2. **Frequent Patterns Count:** `|FPs| = <total_count>`
3. **Execution Time:** `Total Runtime: <seconds:.3f> sec`

### 6.2 File Output
Discovered frequent itemsets are saved to `mining_result_<datasetFileName>.txt`:
- **Line 1:** `|FPs| = <total_count>`
- **Following Lines:** Ordered by itemset length ascending, then numerical item order: `<item1>, <item2>, ... : <support_count>`

---

## 7. Algorithm Architecture & Enhancements

1. **Single-Pass Parsing & Frequency Counting:** Streams the database once to parse unique integer items, count total transactions $N$, compute `minsup_cnt`, and derive the descending F-list.
2. **Projected Transaction Aggregation:** Filters each transaction to frequent items sorted by F-list rank and aggregates identical projected transactions using multiplicity counts before inserting into the FP-tree.
3. **Memory-Compact FP-Tree (`__slots__` + $O(1)$ Dict Children + Tail-Linked Header Table):** Eliminates per-node Python `__dict__` overhead, replaces linear child-list scans with $O(1)$ hash lookups, and appends header links in $O(1)$ via tail pointers.
4. **Single-Prefix-Path Combinatorial Extraction:** Detects single-path FP-trees and conditional FP-trees in $O(1)$ during insertion and directly enumerates all frequent subsets using the deepest node's support, avoiding recursive conditional tree construction.

Refer to `bonus_mark_documentation_too_much_data.pdf` for detailed justifications and empirical benchmarks.

