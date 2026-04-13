#!/usr/bin/env python
# coding: utf-8

# In[10]:


from pathlib import Path
import shutil
import re
import csv

INPUT_DIR = Path("/Users/shahlaazizova/Downloads/ioi2020_day1")
OUTPUT_DIR = INPUT_DIR.parent / f"{INPUT_DIR.name}_best_per_user_task"
CSV_PATH = INPUT_DIR.parent / f"{INPUT_DIR.name}_best_per_user_task.csv"
VALID_TASKS = {"plants", "supertrees", "tickets"}

OUTPUT_DIR.mkdir(exist_ok=True)

# Expected:
# submissionid_task_user-score.task.cpp
# Example:
# 8197_tickets_ARM1-12.0.tickets.cpp

pattern = re.compile(
    r"""
    ^
    (?P<submission_id>\d+)
    _
    (?P<task>[^_]+)
    _
    (?P<user>[^-]+)
    -
    (?P<score>\d+(?:\.\d+)?)
    \.
    .*
    $
    """,
    re.VERBOSE
)

def spreadsheet_safe_text(value: str) -> str:
    return f'="{value}"'

best_files = {}
bad_files = []

for path in INPUT_DIR.iterdir():
    if not path.is_file():
        continue

    m = pattern.match(path.name)
    if not m:
        bad_files.append((path.name, "pattern mismatch"))
        continue

    submission_id = int(m.group("submission_id"))
    task = m.group("task").strip()
    user = m.group("user").strip()
    score_str = m.group("score").strip()

    if task not in VALID_TASKS:
        bad_files.append((path.name, f"unexpected task: {task}"))
        continue

    score_float = float(score_str)
    score_int = int(score_float)   # keep highest integer value of C

    # group by each user's each task
    key = (user, task)

    # compare:
    # 1) integer part of score
    # 2) full score
    # 3) submission id
    candidate = {
        "user": user,
        "task": task,
        "submission_id": submission_id,
        "score_str": score_str,
        "score_float": score_float,
        "score_int": score_int,
        "filename": path.name,
        "path": path,
    }

    if key not in best_files:
        best_files[key] = candidate
    else:
        current = best_files[key]
        if (
            (candidate["score_int"], candidate["score_float"], candidate["submission_id"])
            >
            (current["score_int"], current["score_float"], current["submission_id"])
        ):
            best_files[key] = candidate

# copy winners
rows = []
for item in best_files.values():
    src = item["path"]
    dst = OUTPUT_DIR / src.name
    shutil.copy2(src, dst)

    rows.append({
        "user": spreadsheet_safe_text(item["user"]),
        "task": item["task"],
        "submission_id": item["submission_id"],
        "score": int(float(item["score_str"])),
        "score_int_used": item["score_int"],
        "filename": item["filename"],
    })

# save summary csv
rows = sorted(rows, key=lambda x: (x["user"], x["task"]))

with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=["user", "task", "submission_id", "score", "score_int_used", "filename"]
    )
    writer.writeheader()
    writer.writerows(rows)

print(f"Selected {len(rows)} files.")
print(f"Copied files to: {OUTPUT_DIR}")
print(f"Saved summary CSV to: {CSV_PATH}")

if bad_files:
    print("\nSkipped files:")
    for name, reason in bad_files[:20]:
        print(f" - {name}  [{reason}]")
    if len(bad_files) > 20:
        print(f" ... and {len(bad_files) - 20} more")


# In[4]:


import pandas as pd

df = pd.read_csv("/Users/shahlaazizova/Downloads/ioi2020_day1_best_per_user_task.csv")

counts = df.groupby("user")["task"].nunique().value_counts().sort_index()
print(counts)


# In[6]:


missing = df.groupby("user")["task"].nunique()
missing = missing[missing < 3]
print(missing)


# In[8]:


dupes = df.duplicated(subset=["user", "task"], keep=False)
print(df[dupes].sort_values(["user", "task"]))


# In[ ]:




