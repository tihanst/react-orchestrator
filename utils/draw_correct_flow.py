"""Draw the CLI session and LangGraph turn diagram used by the README.

Run from the project root:
    uv run python utils/draw_correct_flow.py
An optional first argument overrides the output PNG path.
"""
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

NODE_COLOR, NODE_EDGE = "#dcd8f5", "#9b8fe0"
END_COLOR, END_EDGE = "#e8f4e8", "#5a9a5a"
RED = "#cc4444"
W, H, PAD = 3.0, 0.55, 0.08
HW, HH = W / 2 + PAD, H / 2 + PAD
fig, ax = plt.subplots(figsize=(16, 13.4))
fig.patch.set_facecolor("white")
ax.set_xlim(0, 16)
ax.set_ylim(0, 13.4)
ax.set_aspect("equal")
ax.axis("off")


def boundary(x, y, w, h, label):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02",
        facecolor="none", edgecolor="#aaaaaa", linewidth=1.2, zorder=0))
    ax.text(x + 0.22, y + h - 0.3, label, fontsize=12, fontweight=500,
        va="center", color="#444444", bbox=dict(facecolor="white", edgecolor="none", pad=2))


def node(x, y, label, terminal=False, cli=False):
    color, edge = (END_COLOR, END_EDGE) if terminal else (NODE_COLOR, NODE_EDGE)
    if cli:
        color, edge = "#f4f4f4", "#999999"
    ax.add_patch(FancyBboxPatch((x-W/2, y-H/2), W, H,
        boxstyle=f"round,pad={PAD}", facecolor=color, edgecolor=edge,
        linewidth=1.5, zorder=3))
    ax.text(x, y, label, ha="center", va="center", fontsize=11,
        fontfamily="monospace", zorder=4)


def arrow(points, color="black"):
    for p, q in zip(points[:-2], points[1:-1]):
        ax.plot([p[0], q[0]], [p[1], q[1]], color=color, lw=1.5, zorder=2)
    ax.annotate("", xy=points[-1], xytext=points[-2], arrowprops=dict(
        arrowstyle="-|>", lw=1.5, mutation_scale=22, shrinkA=0, shrinkB=0,
        color=color), zorder=2)


def label(x, y, text, ha="left", color="#444444"):
    ax.text(x, y, text, fontsize=11, ha=ha, va="center", color=color,
        zorder=5, bbox=dict(facecolor="white", edgecolor="none", pad=2))


boundary(0.2, 0.2, 15.6, 13.0, "CLI session")
boundary(0.6, 0.6, 13.7, 9.2, "LangGraph turn")
node(5, 11.5, "Wait for user input\nat prompt>", cli=True)
node(11, 11.5, "Save conversation\nand exit", cli=True)
node(5, 8.8, "__start__", terminal=True)
node(5, 7.1, "assistant")
node(11, 7.1, "__end__", terminal=True)
node(5, 4.8, "check_tool_permission")
node(5, 2.6, "tools")
node(11, 3.5, "research_agent_node")
node(11, 1.5, "compile_research")

arrow([(5, 11.5-HH), (5, 8.8+HH)])
label(5.15, 10.25, "submit message")
arrow([(5+HW, 11.5), (11-HW, 11.5)])
label(8, 11.72, "!exit", ha="center")
arrow([(5, 8.8-HH), (5, 7.1+HH)])
arrow([(5, 7.1-HH), (5, 4.8+HH)])
label(5.15, 6.0, "tool call")
arrow([(5+HW, 7.1), (11-HW, 7.1)])
label(8, 7.45, "final response\n(no tool calls)", ha="center")

# Rejection completes the graph turn; it does not invoke assistant again.
arrow([(5+HW, 4.8), (11, 4.8), (11, 7.1-HH)], RED)
label(8.5, 5.13, "rejected; record denial", ha="center", color=RED)

arrow([(5, 4.8-HH), (5, 2.6+HH)])
label(5.15, 3.7, "approved\nstandard tool")
arrow([(5+HW, 4.62), (8.2, 4.62), (8.2, 3.5), (11-HW, 3.5)])
label(8.42, 4.17, "approved research\nfan-out (Send ×N)")
arrow([(11, 3.5-HH), (11, 1.5+HH)])
label(11.15, 2.5, "join results")

arrow([(5-HW, 2.6), (2.7, 2.6), (2.7, 7.1), (5-HW, 7.1)])
label(2.53, 4.0, "tool\nresult", ha="right")
arrow([(11-HW, 1.5), (1.2, 1.5), (1.2, 7.28), (5-HW, 7.28)])
label(1.37, 6.0, "compiled\nresearch")
label(7.6, 1.23, "Next assistant pass writes report", ha="center")
label(11, 3.0, "×N — one worker per query", ha="center")

# The outer loop waits for another prompt after either normal completion or denial.
arrow([(11, 7.1+HH), (11, 9.1), (15, 9.1), (15, 12.4),
       (5, 12.4), (5, 11.5+HH)])
label(12.1, 12.58, "turn complete; wait for next message", ha="center")

# Crop to the outer CLI boundary, keeping only a narrow white margin.
fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
output = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/agent_graph.png")
output.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(output, dpi=150, bbox_inches="tight", pad_inches=0.02, facecolor="white")
plt.close(fig)
print(output)
