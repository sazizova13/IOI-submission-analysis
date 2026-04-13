#!/usr/bin/env python
# coding: utf-8

# For a singular file

# In[2]:


import json
import hashlib
import re
from pathlib import Path

import pandas as pd

from tree_sitter import Language, Parser
import tree_sitter_cpp


# In[ ]:





# In[4]:


INPUT_CODE_FILE = "3349_plants_ZAF3-0.0.plants.cpp"

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CPP_LANGUAGE = Language(tree_sitter_cpp.language())
parser = Parser(CPP_LANGUAGE)

print("Parser ready")


# In[6]:


code_path = Path(INPUT_CODE_FILE)

raw_code = code_path.read_text(
    encoding="utf-8",
    errors="ignore"
)

print("Loaded file:", code_path.name)
print("Characters:", len(raw_code))
print(raw_code[:500])


# In[8]:


raw_code_out = OUTPUT_DIR / "raw_submitted_code.cpp"
raw_code_out.write_text(raw_code, encoding="utf-8")

print("Saved:", raw_code_out)


# In[10]:


def remove_cpp_comments(code: str):
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
    code = re.sub(r"//.*", "", code)
    return code

def normalize_code(code: str):
    code = code.replace("\r\n", "\n").replace("\r", "\n")
    code = remove_cpp_comments(code)
    code = "\n".join(line.rstrip() for line in code.splitlines())
    code = re.sub(r"\n{3,}", "\n\n", code)
    return code.strip() + "\n"

normalized_code = normalize_code(raw_code)

normalized_out = OUTPUT_DIR / "normalized_code.cpp"
normalized_out.write_text(normalized_code, encoding="utf-8")

print("Saved normalized code")


# In[12]:


tree = parser.parse(normalized_code.encode("utf-8"))

root = tree.root_node

code_bytes = normalized_code.encode("utf-8")

print("Root:", root.type)
print("Error:", root.has_error)
print("Children:", len(root.children))


# In[14]:


def node_to_dict(node):

    snippet = code_bytes[node.start_byte:node.end_byte].decode(
        "utf-8",
        errors="ignore"
    )

    snippet = snippet.strip().replace("\n", " ")

    if len(snippet) > 80:
        snippet = snippet[:80] + "..."

    return {
        "type": node.type,
        "text": snippet,
        "children": [node_to_dict(c) for c in node.children]
    }

ast_dict = node_to_dict(root)

ast_path = OUTPUT_DIR / "ast.json"

with open(ast_path, "w") as f:
    json.dump(ast_dict, f, indent=2)

print("Saved AST")


# In[16]:


def walk_ast(node):

    yield node

    for child in node.children:
        yield from walk_ast(child)


def ast_max_depth(node):

    if not node.children:
        return 1

    return 1 + max(ast_max_depth(c) for c in node.children)


def count_nodes_by_type(node, types):

    count = 0

    for n in walk_ast(node):
        if n.type in types:
            count += 1

    return count


# In[18]:


LOOP_TYPES = {"for_statement","while_statement","do_statement"}

COND_TYPES = {"if_statement","switch_statement"}

FUNC_TYPES = {"function_definition"}

RETURN_TYPES = {"return_statement"}

BREAK_TYPES = {"break_statement"}

CONTINUE_TYPES = {"continue_statement"}


# In[20]:


features = {

    "ast_max_depth":
        ast_max_depth(root),

    "num_functions":
        count_nodes_by_type(root,FUNC_TYPES),

    "num_loops":
        count_nodes_by_type(root,LOOP_TYPES),

    "num_conditionals":
        count_nodes_by_type(root,COND_TYPES),

    "num_returns":
        count_nodes_by_type(root,RETURN_TYPES),

    "num_breaks":
        count_nodes_by_type(root,BREAK_TYPES),

    "num_continues":
        count_nodes_by_type(root,CONTINUE_TYPES),

}


# In[22]:


def count_includes(code):
    return len(re.findall(r'#\s*include',code))


def count_macros(code):
    return len(re.findall(r'#\s*define',code))


features["include_count"] = count_includes(normalized_code)

features["macro_count"] = count_macros(normalized_code)


# In[24]:


features_json = OUTPUT_DIR / "features.json"

with open(features_json,"w") as f:
    json.dump(features,f,indent=2)

features_df = pd.DataFrame([features])

features_csv = OUTPUT_DIR / "features.csv"

features_df.to_csv(features_csv,index=False)

print("Saved features")


# In[26]:


feature_order = list(features.keys())

vector = [features[k] for k in feature_order]

vector_string = "|".join(str(x) for x in vector)

fingerprint_hash = hashlib.sha256(
    vector_string.encode()
).hexdigest()

fingerprint = {

    "feature_order": feature_order,

    "vector": vector,

    "vector_string": vector_string,

    "sha256": fingerprint_hash
}


# In[28]:


fp_path = OUTPUT_DIR / "fingerprint.json"

with open(fp_path,"w") as f:
    json.dump(fingerprint,f,indent=2)

print("Saved fingerprint")


# In[30]:


print("Pipeline completed\n")

for f in OUTPUT_DIR.iterdir():
    print("-",f.name)


# For the entire folder

# In[10]:


import json
import hashlib
import re
from pathlib import Path

import pandas as pd
from tree_sitter import Language, Parser
import tree_sitter_cpp

INPUT_DIR = Path("/Users/shahlaazizova/Downloads/ioi2020_day1_best_per_user_task")
OUTPUT_DIR = INPUT_DIR.parent / f"{INPUT_DIR.name}_fingerprints"


OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CPP_LANGUAGE = Language(tree_sitter_cpp.language())
parser = Parser(CPP_LANGUAGE)


def remove_cpp_comments(code: str) -> str:
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
    code = re.sub(r"//.*", "", code)
    return code


def normalize_code(code: str) -> str:
    code = code.replace("\r\n", "\n").replace("\r", "\n")
    code = remove_cpp_comments(code)
    code = "\n".join(line.rstrip() for line in code.splitlines())
    code = re.sub(r"\n{3,}", "\n\n", code)
    return code.strip() + "\n"


def walk_ast(node):
    yield node
    for child in node.children:
        yield from walk_ast(child)


def ast_max_depth(node):
    if not node.children:
        return 1
    return 1 + max(ast_max_depth(c) for c in node.children)


def count_nodes_by_type(node, types):
    count = 0
    for n in walk_ast(node):
        if n.type in types:
            count += 1
    return count


def count_includes(code: str) -> int:
    return len(re.findall(r'#\s*include', code))


def count_macros(code: str) -> int:
    return len(re.findall(r'#\s*define', code))


def node_to_dict(node, code_bytes: bytes):
    snippet = code_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="ignore")
    snippet = snippet.strip().replace("\n", " ")
    if len(snippet) > 80:
        snippet = snippet[:80] + "..."
    return {
        "type": node.type,
        "text": snippet,
        "children": [node_to_dict(c, code_bytes) for c in node.children],
    }


LOOP_TYPES = {"for_statement", "while_statement", "do_statement"}
COND_TYPES = {"if_statement", "switch_statement"}
FUNC_TYPES = {"function_definition"}
RETURN_TYPES = {"return_statement"}
BREAK_TYPES = {"break_statement"}
CONTINUE_TYPES = {"continue_statement"}


all_rows = []
failed_files = []

for code_path in sorted(INPUT_DIR.glob("*.cpp")):
    try:
        raw_code = code_path.read_text(encoding="utf-8", errors="ignore")
        normalized_code = normalize_code(raw_code)

        tree = parser.parse(normalized_code.encode("utf-8"))
        root = tree.root_node
        code_bytes = normalized_code.encode("utf-8")

        features = {
            "ast_max_depth": ast_max_depth(root),
            "num_functions": count_nodes_by_type(root, FUNC_TYPES),
            "num_loops": count_nodes_by_type(root, LOOP_TYPES),
            "num_conditionals": count_nodes_by_type(root, COND_TYPES),
            "num_returns": count_nodes_by_type(root, RETURN_TYPES),
            "num_breaks": count_nodes_by_type(root, BREAK_TYPES),
            "num_continues": count_nodes_by_type(root, CONTINUE_TYPES),
            "include_count": count_includes(normalized_code),
            "macro_count": count_macros(normalized_code),
        }

        feature_order = list(features.keys())
        vector = [features[k] for k in feature_order]
        vector_string = "|".join(str(x) for x in vector)
        fingerprint_hash = hashlib.sha256(vector_string.encode()).hexdigest()

        fingerprint = {
            "file_name": code_path.name,
            "feature_order": feature_order,
            "vector": vector,
            "vector_string": vector_string,
            "sha256": fingerprint_hash,
        }

        stem_dir = OUTPUT_DIR / code_path.stem
        stem_dir.mkdir(parents=True, exist_ok=True)

        (stem_dir / "raw_submitted_code.cpp").write_text(raw_code, encoding="utf-8")
        (stem_dir / "normalized_code.cpp").write_text(normalized_code, encoding="utf-8")

        with open(stem_dir / "ast.json", "w", encoding="utf-8") as f:
            json.dump(node_to_dict(root, code_bytes), f, indent=2)

        with open(stem_dir / "features.json", "w", encoding="utf-8") as f:
            json.dump(features, f, indent=2)

        pd.DataFrame([features]).to_csv(stem_dir / "features.csv", index=False)

        with open(stem_dir / "fingerprint.json", "w", encoding="utf-8") as f:
            json.dump(fingerprint, f, indent=2)

        row = {"file_name": code_path.name, **features, "vector_string": vector_string, "sha256": fingerprint_hash}
        all_rows.append(row)
        print(f"Processed: {code_path.name}")

    except Exception as e:
        failed_files.append({"file_name": code_path.name, "error": str(e)})
        print(f"Failed: {code_path.name} -> {e}")


if all_rows:
    df_all = pd.DataFrame(all_rows)

    # Extract username and task 
    def extract_user_task(name):
        parts = name.split("_")
        if len(parts) >= 3:
            task = parts[1]
            user_score = parts[2]
            user = user_score.split("-")[0]
            return f"{user}_{task}"
        return "UNKNOWN"

    df_all["user_task"] = df_all["file_name"].apply(extract_user_task)

    # Keep only required columns
    cols_to_keep = [
        "user_task",
        "ast_max_depth",
        "num_functions",
        "num_loops",
        "num_conditionals",
        "num_returns",
        "num_breaks",
        "num_continues",
        "include_count",
        "macro_count",
    ]

    df_final = df_all[cols_to_keep]

    # Save new file
    df_final.to_csv(OUTPUT_DIR / "all_fingerprints_summary_clean.csv", index=False)

if failed_files:
    pd.DataFrame(failed_files).to_csv(OUTPUT_DIR / "failed_files.csv", index=False)

print("\nDone")
print(f"Output folder: {OUTPUT_DIR}")
print(f"Processed files: {len(all_rows)}")
print(f"Failed files: {len(failed_files)}")







