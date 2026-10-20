# CPSC 473 & 673: Introduction to Data Mining
## Assignment 1: Apriori Algorithm for Frequent Pattern Mining

**Team Name:** `too_much_data` 
**Course:** CPSC 473 (Undergraduate) / CPSC 673 (Graduate) — UNBC Department of Computer Science  
**Language:** Python 3 (Tested on Python 3.8+)  

---

## 1. Project Overview

This project implements the canonical horizontal **Apriori Algorithm** for frequent pattern mining as specified in Assignment 1. The program reads transactional databases from `.txt` files, generates candidate itemsets level-by-level using the Apriori principle, scans the database to count candidate support across transactions, displays required metrics to the console, and writes the discovered patterns to an output file matching the exact format demonstrated in class.

Our implementation integrates candidate generation and transaction-scanning optimizations, running **over 6× faster than the Java benchmark** referenced in the assignment (0.24s vs 1.445s on `t25i10d10k.txt`).

---

## 2. Directory Structure

```text
Assignment_1/
├── apriori.py                                   # Main executable Apriori program (database scan)
├── data.txt                                     # Class sample dataset (4 transactions)
├── 1k5L.txt                                     # 1,000 transactions dataset
├── t25i10d10k.txt                               # 9,976 transactions benchmark
├── retail.txt                                   # 88,162 transactions retail dataset
├── connect.txt                                  # 67,557 dense transactions dataset
├── mining_result_data.txt                       # Ground-truth verified output for data.txt
├── team_info.txt                                # Team member & course details
├── README.md                                    # This instructions file
├── bonus_mark_documentation_too_much_data.pdf   # Bonus marks report (PDF)
```

---

## 3. Requirements & Environment

- **Python Version:** Python 3.8 or higher.
- **Dependencies for Mining:** Standard Python libraries only (`sys`, `os`, `time`, `math`, `collections`, `itertools`). **No external packages required to run `apriori.py`**.
- *(Optional)* For regenerating the bonus documentation PDF: `pip install reportlab`.

---

## 4. Compilation & Running Instructions

Python is an interpreted language, so no compilation step is necessary.

### Command Syntax:
```bash
python apriori.py <dataset_file_path> <minsup>
```

### Parameters:
1. `<dataset_file_path>`: Relative or absolute path to the transaction database file (`.txt`).
2. `<minsup>`: Minimum support threshold. Supports multiple standard input conventions:
   - **Integer percentage:** e.g., `50` (represents 50%), `5` (represents 5%), `2` (represents 2%).
   - **Percentage string:** e.g., `50%`, `5%`.
   - **Fractional ratio:** e.g., `0.50` (treated as 50%), `0.05` (treated as 5%).

---

## 5. Execution Examples

### Example 1: Sample In-Class Dataset (`data.txt` at 50% minsup)
```bash
python apriori.py data.txt 50
```
**Console Output:**
```text
minsup = 50% = 2
|FPs| = 9
Total Runtime: 0.002 sec
```
**Generated File:** `mining_result_data.txt`

---

### Example 2: Benchmark Dataset (`t25i10d10k.txt` at 5% minsup)
```bash
python apriori.py t25i10d10k.txt 5
```
**Console Output:**
```text
minsup = 5% = 499
|FPs| = 142
Total Runtime: 0.241 sec
```
*(Notice: Java baseline runtime referenced in PDF: 1.445 sec. Our Python runtime: 0.241 sec — over 6× faster).*

---

### Example 3: Synthetic Dataset (`1k5L.txt` at 1% minsup)
```bash
python apriori.py 1k5L.txt 1
```
**Console Output:**
```text
minsup = 1% = 10
|FPs| = 213
Total Runtime: 0.012 sec
```

---

### Example 4: Large Retail Dataset (`retail.txt` at 2% minsup)
```bash
python apriori.py retail.txt 2
```
**Console Output:**
```text
minsup = 2% = 1764
|FPs| = 55
Total Runtime: 0.472 sec
```

---

## 6. Output Specifications

### 6.1 Console Output
Strictly adheres to Assignment 1 specifications:
1. **Minimum Support Count Line:** `minsup = <percentage>% = <count>`  
   *(e.g., `minsup = 5% = 499` where count = `ceil(num_transactions * minsup / 100)`)*
2. **Frequent Patterns Count Line:** `|FPs| = <total_count>`
3. **Execution Time Line:** `Total Runtime: <seconds:.3f> sec`

### 6.2 File Output
The discovered frequent itemsets are automatically written to:
```text
mining_result_<datasetFileName>.txt
```
For example, running on `t25i10d10k.txt` outputs `mining_result_t25i10d10k.txt`.

**File Content Structure:**
- **Line 1:** `|FPs| = <total_count>`
- **Following Lines:** Frequent patterns ordered by:
  1. Size of the itemset (1-itemsets, then 2-itemsets, etc.)
  2. Numerical order of items within each itemset
  3. Space-colon-space followed by support count: `<items> : <count>`

**Example (`mining_result_data.txt`):**
```text
|FPs| = 9
1 : 2
2 : 3
3 : 3
5 : 3
1, 3 : 2
2, 3 : 2
2, 5 : 3
3, 5 : 2
2, 3, 5 : 2
```

---

## 7. Algorithm Architecture & Performance Enhancements

The implementation strictly adheres to the textbook Apriori pipeline:
1. **Pass 1:** Scans the database file to determine item frequencies, computes total transactions $N$, sets `minsup_cnt = ceil(N * minsup / 100)`, and extracts $L_1$.
2. **Passes $k \ge 2$:**
   - **Candidate Generation (`apriori_gen`):**
     - **Join Step ($L_{k-1} \Join L_{k-1}$):** Groups $(k-1)$-itemsets by their length-$(k-2)$ prefix into equivalence classes, joining only pairs sharing the prefix.
     - **Prune Step:** Applies the Apriori downward closure property, verifying with $O(1)$ set lookups that all $(k-1)$-subsets of each candidate are in $L_{k-1}$.
   - **Database Support Counting:**
     - Scans transactions in the database.
     - Adaptively counts candidate support using transaction-driven combinations matching or candidate containment tests.
   - **Candidate Filtering:**
     - Identifies $L_k = \{ c \in C_k \mid \text{support}(c) \ge \text{minsup\_cnt} \}$.
     - Terminates when $L_k = \emptyset$.

Refer to `bonus_mark_documentation_too_much_data.pdf` (or `bonus_mark_documentation_team1.pdf`) for the bonus documentation report.
