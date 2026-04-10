# IOI-submission-analysis
Empirical analysis of IOI coding behavior using AST-based structural fingerprinting and code and performance evolution tracking.

## Code and Performance Evolution Analyzer

A Streamlit dashboard for analyzing how contestants' source code evolves across consecutive submissions in IOI competitions.

Built as part of a research paper on coding behavior under time constraints in the International Olympiad in Informatics.

---

### What it does

For each contestant and task, the tool:
- Cleans and tokenizes each submitted source file
- Computes token-level additions and deletions between consecutive submissions
- Computes structural similarity between consecutive submissions
- Visualizes both alongside the score trajectory

---

### Pipeline

```
Submissions (CMS export)
        ↓
Pre-processing
  1. Remove // comments
  2. Remove /* */ comments
  3. Remove # preprocessor directives
  4. Normalize whitespace and tabs
  5. Strip blank lines
        ↓
Tokenization
  identifiers → ID
  numbers     → NUM
  operators   → kept as-is
        ↓
Token diff (submission N vs N−1)
  → additions count
  → deletions count
  → similarity score (Ratcliff-Obershelp, 0–100%)
        ↓
Visualization
```

---

### Setup

```bash
pip install streamlit plotly
```

Set your submissions folder at the top of the file:

```python
SUBMISSIONS_DIR = "path/to/your/submissions"
```

Or change it at runtime via the sidebar.

```bash
streamlit run code_and_performance_evolution.py
```

---

### Dataset

Developed and tested on the **IOI 2020 Day 1** dataset, containing submissions for three tasks: `plants`, `supertrees`, and `tickets`.

---

### Team

Shahla Azizova
Seyidshah Muradov
Jamaladdin Hasanov
