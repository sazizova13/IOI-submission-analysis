import os
import re
import difflib
import tokenize
from io import StringIO
from collections import defaultdict


# Filename Parser
# Example Filename: 3349_plants_ZAF3-0.0.plants
def parse_filename(filename):
    pattern = r'^(\d+)_([^_]+)_([A-Z]{2,4}\d+)-([\d.]+)\.(.+)$'
    m = re.match(pattern, filename)
    if m:
        return {
            "submission_id": int(m.group(1)),
            "task":          m.group(2),
            "user":          m.group(3),
            "score":         float(m.group(4)),
            "ext":           m.group(5),
            "filename":      filename,
        }
    return None


def read_file(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def load_submissions(folder):
    raw_files = sorted(os.listdir(folder))
    submissions = []
    for f in raw_files:
        if not os.path.isfile(os.path.join(folder, f)):
            continue
        parsed = parse_filename(f)
        if parsed:
            submissions.append(parsed)

    by_user_task = defaultdict(lambda: defaultdict(list))
    for s in submissions:
        by_user_task[s["user"]][s["task"]].append(s)

    for user in by_user_task:
        for task in by_user_task[user]:
            by_user_task[user][task].sort(key=lambda x: x["submission_id"])

    return submissions, by_user_task


# Pre-processing pipeline — 5 steps
def clean_code(code):
    """
    Remove comments and normalize whitespace from source code.

    Step 1 — Remove single-line comments (//)
    Step 2 — Remove multi-line comments (/* */)
    Step 3 — Remove preprocessor directives (#include, #define, ...)
    Step 4 — Normalize tabs to spaces, collapse multiple spaces
    Step 5 — Strip blank lines and trailing whitespace per line
    """
    code = re.sub(r'//[^\n]*', '', code)
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    code = re.sub(r'#[^\n]*', '', code)
    code = code.replace('\t', ' ')
    code = re.sub(r'[ ]+', ' ', code)
    lines = [line.strip() for line in code.splitlines()]
    lines = [line for line in lines if line]
    return '\n'.join(lines)


# Tokenization
def tokenize_code(code):
    """
    Convert cleaned source code into a normalized token sequence.

    - All identifiers and keywords → ID
    - All numeric literals         → NUM
    - Operators                    → kept as-is

    Two structurally identical programs produce identical token
    sequences regardless of variable naming conventions.
    """
    tokens = []
    cleaned = clean_code(code)
    try:
        for tok in tokenize.generate_tokens(StringIO(cleaned).readline):
            if tok.type == tokenize.NAME:
                tokens.append("ID")
            elif tok.type == tokenize.NUMBER:
                tokens.append("NUM")
            elif tok.type == tokenize.OP:
                tokens.append(tok.string)
    except Exception:
        pass
    return tokens


# Core analysis
def analyze_submission_pair(old_code, new_code):
    """
    Compare two consecutive submissions at the token level.

    Pipeline: clean → tokenize → diff token sequences

    Both the addition/deletion counts and the similarity score are
    derived from the same token sequences, making them consistent
    and directly comparable.

    Returns:
        plus       (list) — added tokens
        minus      (list) — removed tokens
        similarity (float) — SequenceMatcher ratio, 0-100%
    """
    old_tokens = tokenize_code(old_code)
    new_tokens = tokenize_code(new_code)

    # Token-level diff
    diff = difflib.unified_diff(old_tokens, new_tokens, lineterm="")
    minus, plus = [], []
    for line in diff:
        if line.startswith(("---", "+++", "@@")):
            continue
        if line.startswith("-"):
            minus.append(line[1:].strip())
        elif line.startswith("+"):
            plus.append(line[1:].strip())

    # Similarity — by-product of the same token sequences
    similarity = round(
        difflib.SequenceMatcher(None, old_tokens, new_tokens).ratio() * 100, 1
    )
    return plus, minus, similarity
