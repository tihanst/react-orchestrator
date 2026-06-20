import os

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

fig, ax = plt.subplots(figsize=(13, 14))
ax.set_xlim(0, 13)
ax.set_ylim(0, 14)
ax.axis("off")
fig.patch.set_facecolor("white")

NODE_COLOR = "#dcd8f5"
NODE_EDGE  = "#9b8fe0"
END_COLOR  = "#e8f4e8"
END_EDGE   = "#5a9a5a"
NODE_W, NODE_H = 3.0, 0.55

CX = 5.5   # main column center x
RX = 9.5   # right branch center x (research)


def draw_node(ax, x, y, label, color=NODE_COLOR, edge=NODE_EDGE):
    box = FancyBboxPatch(
        (x - NODE_W / 2, y - NODE_H / 2), NODE_W, NODE_H,
        boxstyle="round,pad=0.08",
        facecolor=color, edgecolor=edge, linewidth=1.5, zorder=3,
    )
    ax.add_patch(box)
    ax.text(x, y, label, ha="center", va="center", fontsize=9.5,
            fontfamily="monospace", zorder=4)


def straight_arrow(ax, x1, y1, x2, y2, color="black"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=1.3), zorder=2)


def edge_label(ax, x, y, text, ha="left", color="#555555", rotation=0):
    ax.text(x, y, text, ha=ha, va="center", fontsize=8,
            color=color, rotation=rotation, zorder=5)


def polyline_arrow(ax, pts, color="black"):
    for i in range(len(pts) - 2):
        ax.plot([pts[i][0], pts[i + 1][0]], [pts[i][1], pts[i + 1][1]],
                color=color, lw=1.3, zorder=2)
    ax.annotate("", xy=pts[-1], xytext=pts[-2],
                arrowprops=dict(arrowstyle="-|>", color=color, lw=1.3), zorder=2)


# ── node positions ────────────────────────────────────────────────────────────
#   main column at CX, right branch at RX

nodes = {
    "__start__":             (CX, 13.5),
    "assistant":             (CX, 12.0),
    "check_tool_permission": (CX,  9.5),
    "tools":                 (CX,  7.0),
    "__end__":               (RX, 12.0),
    "research_agent_node":   (RX,  7.0),
    "compile_research":      (RX,  5.0),
}

for name, (x, y) in nodes.items():
    if name in ("__start__", "__end__"):
        draw_node(ax, x, y, name, color=END_COLOR, edge=END_EDGE)
    else:
        draw_node(ax, x, y, name)

# ── edges ─────────────────────────────────────────────────────────────────────

# __start__ → assistant
straight_arrow(ax, CX, 13.5 - NODE_H / 2, CX, 12.0 + NODE_H / 2)

# assistant → check_tool_permission  (straight down, "tool calls")
straight_arrow(ax, CX, 12.0 - NODE_H / 2, CX, 9.5 + NODE_H / 2)
edge_label(ax, CX + 0.1, (12.0 - NODE_H / 2 + 9.5 + NODE_H / 2) / 2, "tool calls")

# assistant → __end__  (straight right, "no tools")
straight_arrow(ax, CX + NODE_W / 2, 12.0, RX - NODE_W / 2, 12.0)
edge_label(ax, (CX + NODE_W / 2 + RX - NODE_W / 2) / 2, 12.15, "no tools", ha="center")

# check_tool_permission → tools  (straight down, "approved")
straight_arrow(ax, CX, 9.5 - NODE_H / 2, CX, 7.0 + NODE_H / 2)
edge_label(ax, CX + 0.1, (9.5 - NODE_H / 2 + 7.0 + NODE_H / 2) / 2, "approved")

# check_tool_permission → research_agent_node  (right outer rail, "fan-out / Send")
FAN_RAIL = 11.8
polyline_arrow(ax, [
    (CX + NODE_W / 2, 9.5),      # exit right of check_tool_permission
    (FAN_RAIL, 9.5),              # swing right past right column
    (FAN_RAIL, 7.0),              # down to research level
    (RX + NODE_W / 2, 7.0),      # enter research_agent_node from right
])
edge_label(ax, FAN_RAIL + 0.1, 8.25, "fan-out\n(Send)", ha="left")

# research_agent_node → compile_research  (straight down)
straight_arrow(ax, RX, 7.0 - NODE_H / 2, RX, 5.0 + NODE_H / 2)

# compile_research → assistant  (far-left loop)
LEFT_COMP = 1.2
polyline_arrow(ax, [
    (RX - NODE_W / 2, 5.0),      # exit left of compile_research
    (LEFT_COMP, 5.0),
    (LEFT_COMP, 12.0),
    (CX - NODE_W / 2, 12.0),     # enter assistant from left
])
edge_label(ax, LEFT_COMP - 0.1, 8.5, "compile →\nassistant", ha="right")

# tools → assistant  (left loop)
LEFT_TOOLS = 2.2
polyline_arrow(ax, [
    (CX - NODE_W / 2, 7.0),      # exit left of tools
    (LEFT_TOOLS, 7.0),
    (LEFT_TOOLS, 12.0),
    (CX - NODE_W / 2, 12.0),     # enter assistant from left
])
edge_label(ax, LEFT_TOOLS - 0.1, 9.5, "tools →\nassistant", ha="right")

# check_tool_permission → assistant  (left loop, rejected, red)
LEFT_REJ = 3.2
polyline_arrow(ax, [
    (CX - NODE_W / 2, 9.5),      # exit left of check_tool_permission
    (LEFT_REJ, 9.5),
    (LEFT_REJ, 12.0),
    (CX - NODE_W / 2, 12.0),     # enter assistant from left
], color="#cc4444")
edge_label(ax, LEFT_REJ - 0.1, 10.75, "rejected", ha="right", color="#cc4444")

output_path = "docs/agent_graph.png"
output_dir = os.path.dirname(output_path)
os.makedirs(output_dir, exist_ok=True)

plt.tight_layout()
plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
