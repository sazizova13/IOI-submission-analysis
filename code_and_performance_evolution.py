import os
import re
import difflib
import tokenize
from io import StringIO
from collections import Counter, defaultdict
import streamlit as st
import plotly.graph_objects as go

SUBMISSIONS_DIR = "C:/Users/MSI/Desktop/IOI Analysis/ioi2020_day1/ioi2020_day1"

st.set_page_config(
    page_title="IOI Code Evolution Analyzer",
    page_icon="🏆",
    layout="wide"
)

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

def clean_code(code):
    code = re.sub(r'//[^\n]*', '', code)
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    code = re.sub(r'#[^\n]*', '', code)
    code = code.replace('\t', ' ')
    code = re.sub(r'[ ]+', ' ', code)
    lines = [line.strip() for line in code.splitlines()]
    lines = [line for line in lines if line]
    return '\n'.join(lines)

def tokenize_code(code):
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

def analyze_submission_pair(old_code, new_code):

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

# ──────────────────────────────────────────────
# Chart theme — white background

CHART = dict(
    bg         = "#FFFFFF",
    grid       = "#E5E5E5",
    axis_line  = "#AAAAAA",
    font_color = "#222222",
    tick_color = "#444444",
    zero_line  = "#999999",
    added      = "#2CA02C",
    removed    = "#D62728",
    score      = "#FF7F0E",
    sim        = "#1F77B4",
    sim_fill   = "rgba(31,119,180,0.10)",
)

def base_layout(height=420, margin=None):
    if margin is None:
        margin = dict(l=65, r=70, t=45, b=65)
    return dict(
        paper_bgcolor = CHART["bg"],
        plot_bgcolor  = CHART["bg"],
        font          = dict(color=CHART["font_color"], family="Arial, sans-serif", size=12),
        height        = height,
        margin        = margin,
        hovermode     = "x unified",
        legend        = dict(
            orientation="h", yanchor="bottom", y=1.03,
            xanchor="right", x=1,
            font=dict(size=11, color=CHART["font_color"]),
            bgcolor="rgba(255,255,255,0.85)",
            bordercolor=CHART["axis_line"], borderwidth=0.5,
        ),
    )

def x_axis(title="Submission ID"):
    return dict(
        title      = dict(text=title, font=dict(size=12, color=CHART["tick_color"])),
        tickfont   = dict(size=11, color=CHART["tick_color"]),
        showgrid   = False,
        zeroline   = False,
        linecolor  = CHART["axis_line"],
        linewidth  = 1,
        showline   = True,
        ticks      = "outside",
        ticklen    = 4,
    )

def y_axis(title, rng=None, suffix=""):
    d = dict(
        title      = dict(text=title, font=dict(size=12, color=CHART["tick_color"])),
        tickfont   = dict(size=11, color=CHART["tick_color"]),
        showgrid   = True,
        gridcolor  = CHART["grid"],
        gridwidth  = 0.8,
        zeroline   = True,
        zerolinecolor = CHART["zero_line"],
        zerolinewidth = 1.2,
        linecolor  = CHART["axis_line"],
        linewidth  = 1,
        showline   = True,
        ticks      = "outside",
        ticklen    = 4,
        ticksuffix = suffix,
    )
    if rng:
        d["range"] = rng
    return d

def y2_axis(title, rng=None):
    d = dict(
        title      = dict(text=title, font=dict(size=12, color=CHART["tick_color"])),
        overlaying = "y",
        side       = "right",
        tickfont   = dict(size=11, color=CHART["tick_color"]),
        showgrid   = False,
        zeroline   = False,
        linecolor  = CHART["axis_line"],
        linewidth  = 1,
        showline   = True,
        ticks      = "outside",
        ticklen    = 4,
    )
    if rng:
        d["range"] = rng
    return d

# ──────────────────────────────────────────────
# App styling

st.markdown("""
<style>
    .metric-card {
        background: #F7F8FA;
        border-radius: 8px;
        padding: 16px 20px;
        border: 1px solid #DEE2E6;
        text-align: center;
    }
    .metric-value { font-size: 28px; font-weight: 800; color: #222; }
    .metric-label { font-size: 12px; color: #666; margin-top: 4px; }
    .green  { color: #2CA02C; }
    .red    { color: #D62728; }
    .purple { color: #7B4EA0; }
    .yellow { color: #E07B00; }
</style>
""", unsafe_allow_html=True)

st.markdown("## 🏆 IOI/ICPC Code Evolution Analyzer")
st.markdown("Analyze how contestants' code evolved across submissions — per user, per task.")
st.divider()

with st.sidebar:
    st.markdown("### ⚙️ Settings")
    folder = st.text_input("Submissions folder", value=SUBMISSIONS_DIR)
    st.markdown("---")
    st.markdown("**File format expected:**")
    st.code("{id}_{task}_{user}-{score}.{ext}\ne.g. 3349_plants_ZAF3-0.0.plants")
    st.markdown("---")
    st.markdown("**Analysis pipeline:**")
    st.markdown("1. Remove `//` comments")
    st.markdown("2. Remove `/* */` comments")
    st.markdown("3. Remove `#` preprocessor lines")
    st.markdown("4. Normalize whitespace & tabs")
    st.markdown("5. Strip blank lines")

if not os.path.exists(folder):
    st.error(f"❌ Folder not found: `{folder}`")
    st.stop()

raw_files = sorted(os.listdir(folder))
submissions = []
for f in raw_files:
    if not os.path.isfile(os.path.join(folder, f)):
        continue
    parsed = parse_filename(f)
    if parsed:
        submissions.append(parsed)

if not submissions:
    st.error("❌ No files matched the expected naming pattern: `{id}_{task}_{user}-{score}.{ext}`")
    st.stop()

by_user_task = defaultdict(lambda: defaultdict(list))
for s in submissions:
    by_user_task[s["user"]][s["task"]].append(s)

for user in by_user_task:
    for task in by_user_task[user]:
        by_user_task[user][task].sort(key=lambda x: x["submission_id"])

all_users = sorted(by_user_task.keys())

col_sel1, col_sel2 = st.columns([1, 3])
with col_sel1:
    selected_user = st.selectbox("👤 Select User", all_users)

user_tasks = sorted(by_user_task[selected_user].keys())

if not user_tasks:
    st.warning(f"No submissions found for {selected_user}.")
    st.stop()

user_subs   = [s for task in user_tasks for s in by_user_task[selected_user][task]]
total_subs  = len(user_subs)
tasks_count = len(user_tasks)
best_scores = {task: max(s["score"] for s in by_user_task[selected_user][task]) for task in user_tasks}

m1, m2 = st.columns(2)
with m1:
    st.markdown(f"""<div class="metric-card">
        <div class="metric-value purple">{total_subs}</div>
        <div class="metric-label">Total Submissions</div>
    </div>""", unsafe_allow_html=True)
with m2:
    st.markdown(f"""<div class="metric-card">
        <div class="metric-value yellow">{tasks_count}</div>
        <div class="metric-label">Tasks Attempted</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

st.markdown(f"### 📂 Tasks for **{selected_user}**")
tabs = st.tabs([f"🗂 {task}  (best: {best_scores[task]:.1f})" for task in user_tasks])

for tab, task in zip(tabs, user_tasks):
    with tab:
        task_subs = by_user_task[selected_user][task]

        if len(task_subs) < 2:
            s = task_subs[0]
            st.info(f"Only 1 submission for task **{task}**: `{s['filename']}` — Score: **{s['score']}**")
            continue

        diffs = []
        for i in range(1, len(task_subs)):
            old_s    = task_subs[i-1]
            new_s    = task_subs[i]
            old_path = os.path.join(folder, old_s["filename"])
            new_path = os.path.join(folder, new_s["filename"])
            old_code = read_file(old_path)
            new_code = read_file(new_path)
            plus, minus, sim = analyze_submission_pair(old_code, new_code)
            diffs.append({
                "x_label":    f"#{new_s['submission_id']}",
                "sub_id":     new_s["submission_id"],
                "old_sub_id": old_s["submission_id"],
                "old_file":   old_s["filename"],
                "new_file":   new_s["filename"],
                "n_plus":     len(plus),
                "n_minus":    len(minus),
                "score":      new_s["score"],
                "old_score":  old_s["score"],
                "similarity": sim,
            })

        x_labels = [d["x_label"] for d in diffs]
        scores   = [s["score"] for s in task_subs]
        max_bar  = max(
            max((d["n_plus"]  for d in diffs), default=1),
            max((d["n_minus"] for d in diffs), default=1)
        )

        # ── CHART 1: Lines Added / Removed + Score overlay ──────────────
        st.markdown(f"#### Token Additions / Deletions — {task} ({selected_user})")
        st.caption("Green bars ↑ = tokens added between submissions   |   Red bars ↓ = tokens removed   |   Orange line = score (right axis)")

        fig = go.Figure()

        fig.add_trace(go.Bar(
            name="Lines added",
            x=x_labels,
            y=[d["n_plus"] for d in diffs],
            marker_color=CHART["added"],
            marker_line_width=0,
            opacity=0.85,
            hovertemplate="<b>%{x}</b><br>Lines added: <b>+%{y}</b><extra></extra>",
        ))

        fig.add_trace(go.Bar(
            name="Lines removed",
            x=x_labels,
            y=[-d["n_minus"] for d in diffs],
            marker_color=CHART["removed"],
            marker_line_width=0,
            opacity=0.85,
            hovertemplate="<b>%{x}</b><br>Lines removed: <b>%{customdata}</b><extra></extra>",
            customdata=[f"-{d['n_minus']}" for d in diffs],
        ))

        fig.add_trace(go.Scatter(
            name="Score",
            x=[f"#{s['submission_id']}" for s in task_subs],
            y=scores,
            mode="lines+markers+text",
            line=dict(color=CHART["score"], width=2, dash="dot"),
            marker=dict(size=7, color=CHART["score"],
                        line=dict(color="white", width=1.2)),
            text=[f"{sc:.0f}" for sc in scores],
            textposition="top center",
            textfont=dict(color=CHART["score"], size=10),
            yaxis="y2",
            hovertemplate="<b>%{x}</b><br>Score: <b>%{y}</b><extra></extra>",
        ))

        layout = base_layout(height=400)
        layout.update(
            barmode  = "relative",
            xaxis    = x_axis("Submission ID"),
            yaxis    = y_axis("Tokens changed", rng=[-(max_bar + 3), max_bar + 3]),
            yaxis2   = y2_axis("Score", rng=[
                min(scores) - 8 if scores else 0,
                max(scores) + 15 if scores else 100
            ]),
        )
        fig.update_layout(**layout)

        # Border around the chart area
        fig.update_layout(
            shapes=[dict(
                type="rect", xref="paper", yref="paper",
                x0=0, y0=0, x1=1, y1=1,
                line=dict(color=CHART["axis_line"], width=0.8),
            )]
        )

        st.plotly_chart(fig, use_container_width=True)

        # ── CHART 2: Token Similarity ────────────────────────────────────
        st.markdown(f"#### Token-Based Similarity Between Consecutive Submissions — {task} ({selected_user})")
        st.caption("Structural similarity of token sequences between consecutive submissions (100% = identical structure)")

        sim_fig = go.Figure()
        sim_fig.add_trace(go.Scatter(
            name="Token similarity",
            x=x_labels,
            y=[d["similarity"] for d in diffs],
            mode="lines+markers",
            line=dict(color=CHART["sim"], width=2),
            marker=dict(size=7, color=CHART["sim"],
                        line=dict(color="white", width=1.2)),
            fill="tozeroy",
            fillcolor=CHART["sim_fill"],
            hovertemplate="<b>%{x}</b><br>Token similarity: <b>%{y}%</b><extra></extra>",
        ))

        sim_layout = base_layout(height=280, margin=dict(l=65, r=30, t=30, b=65))
        sim_layout.update(
            xaxis  = x_axis("Submission ID"),
            yaxis  = y_axis("Similarity (%)", rng=[0, 108], suffix="%"),
            legend = dict(
                orientation="h", yanchor="bottom", y=1.03,
                xanchor="right", x=1,
                font=dict(size=11, color=CHART["font_color"]),
                bgcolor="rgba(255,255,255,0.85)",
                bordercolor=CHART["axis_line"], borderwidth=0.5,
            ),
        )
        sim_fig.update_layout(**sim_layout)
        sim_fig.update_layout(
            shapes=[dict(
                type="rect", xref="paper", yref="paper",
                x0=0, y0=0, x1=1, y1=1,
                line=dict(color=CHART["axis_line"], width=0.8),
            )]
        )

        st.plotly_chart(sim_fig, use_container_width=True)

        # ── Code Transformation Inspector ────────────────────────────────
        with st.expander("🔬 Code Transformation Inspector — see original → cleaned → tokenized"):
            all_filenames_task = [s["filename"] for s in task_subs]
            chosen_file = st.selectbox(
                "Select a submission to inspect:",
                all_filenames_task,
                key=f"inspector_{task}_{selected_user}"
            )
            if chosen_file:
                raw_i     = read_file(os.path.join(folder, chosen_file))
                cleaned_i = clean_code(raw_i)
                tokens_i  = tokenize_code(raw_i)
                token_str_i = ' '.join(tokens_i)
                ci1, ci2, ci3 = st.columns(3)
                with ci1:
                    st.markdown("**Original code**")
                    st.code(raw_i[:1500] + ("..." if len(raw_i) > 1500 else ""), language="cpp")
                with ci2:
                    st.markdown("**Cleaned code**")
                    st.code(cleaned_i[:1500] + ("..." if len(cleaned_i) > 1500 else ""), language="cpp")
                with ci3:
                    st.markdown("**Token sequence**")
                    st.code(token_str_i[:1500] + ("..." if len(token_str_i) > 1500 else ""))
                st.caption(
                    f"Original: {len(raw_i.splitlines())} lines   →   "
                    f"Cleaned: {len(cleaned_i.splitlines())} lines   →   "
                    f"Tokens: {len(tokens_i)}"
                )

        st.markdown("---")
