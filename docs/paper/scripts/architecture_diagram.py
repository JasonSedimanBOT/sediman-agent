"""
Generate publication-quality architecture and lifecycle diagrams.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, ConnectionPatch
from matplotlib.path import Path
import matplotlib.patheffects as pe
import numpy as np
from pathlib import Path

FIGURES_DIR = Path(__file__).resolve().parent.parent / "figures"

# --- Professional color palette ---
PALETTE = {
    "input":      "#4A90D9",
    "manager":    "#E8833A",
    "agent":      "#D4732E",
    "skills":     "#27AE60",
    "memory":     "#8E44AD",
    "subagent":   "#2980B9",
    "browser":    "#C0392B",
    "llm":        "#F5A623",
    "healing":    "#16A085",
    "bg":         "#F8F9FA",
    "border":     "#2C3E50",
    "arrow":      "#7F8C8D",
    "text_dark":  "#2C3E50",
    "text_light": "#FFFFFF",
}

FONTS = {
    "title": {"fontsize": 11, "fontweight": "bold", "color": PALETTE["text_light"]},
    "body":  {"fontsize": 8, "fontweight": "normal", "color": PALETTE["text_light"]},
    "label": {"fontsize": 7, "fontweight": "normal", "color": PALETTE["text_dark"]},
}


def _box(ax, x, y, w, h, color, title="", body="", title_font=None, body_font=None):
    shadow = FancyBboxPatch(
        (x + 0.04, y - 0.04), w, h,
        boxstyle="round,pad=0.12",
        facecolor="#D5D8DC", edgecolor="none", alpha=0.4, zorder=1,
    )
    ax.add_patch(shadow)

    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.12",
        facecolor=color, edgecolor=PALETTE["border"],
        linewidth=1.0, alpha=0.95, zorder=2,
    )
    ax.add_patch(box)

    tf = title_font or FONTS["title"]
    bf = body_font or FONTS["body"]

    if title and body:
        ax.text(x + w / 2, y + h * 0.62, title, ha="center", va="center", zorder=3, **tf)
        ax.text(x + w / 2, y + h * 0.32, body, ha="center", va="center", zorder=3, **bf)
    elif title:
        ax.text(x + w / 2, y + h / 2, title, ha="center", va="center", zorder=3, **tf)
    elif body:
        ax.text(x + w / 2, y + h / 2, body, ha="center", va="center", zorder=3, **bf)


def _arrow(ax, x1, y1, x2, y2, color=None, label="", style="-|>", lw=1.2, rad=0.0):
    c = color or PALETTE["arrow"]
    arrowprops = dict(
        arrowstyle=style,
        color=c,
        lw=lw,
        connectionstyle=f"arc3,rad={rad}",
        shrinkA=6,
        shrinkB=6,
    )
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=arrowprops, zorder=4)
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(mx, my + 0.12, label, ha="center", va="bottom", zorder=5, **FONTS["label"])


def draw_architecture():
    fig, ax = plt.subplots(1, 1, figsize=(11, 7.5))
    ax.set_xlim(-0.2, 11.2)
    ax.set_ylim(-0.2, 7.7)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    # ── Layer 1: Input ──
    _box(ax, 0.0, 6.5, 1.8, 0.7, PALETTE["input"],
         title="User Input",
         body="(CLI / TUI / API / Discord)")

    # ── Layer 2: Manager ──
    _box(ax, 2.3, 6.3, 2.8, 1.0, PALETTE["manager"],
         title="Manager Agent",
         body="Strategy Selection · Decomposition · Scheduling")

    # ── Layer 3: Agent Loop ──
    _box(ax, 2.3, 4.5, 2.8, 1.3, PALETTE["agent"],
         title="Agent Loop",
         body="Plan → Execute → Observe → Reflect\nBudget · Checkpoints · Milestones")

    # ── LLM Provider ──
    _box(ax, 5.7, 6.3, 2.0, 1.0, PALETTE["llm"],
         title="LLM Providers",
         body="OpenAI · Ollama · Anthropic")

    # ── Skills Engine ──
    _box(ax, 0.0, 3.3, 1.8, 2.5, PALETTE["skills"],
         title="Skill Engine",
         body="Learn · Create · Heal\nExecute · Audit · Search\nVersion · Patch · Rollback")

    # ── Subagents ──
    _box(ax, 5.7, 4.2, 2.0, 1.8, PALETTE["subagent"],
         title="Subagents",
         body="browser · code\ndebug · explore\nintegrate · review\nredteam")

    # ── Memory System ──
    _box(ax, 8.2, 4.2, 2.8, 2.3, PALETTE["memory"],
         title="Tiered Memory",
         body="Working → Session → Long-Term\n\nVector Search (OpenAI/FastEmbed/TF-IDF)\nBackground Review · Consolidation\nSecurity Scanner · Context Filter")

    # ── Browser Layer ──
    _box(ax, 0.0, 1.0, 11.0, 1.7, PALETTE["browser"],
         title="",
         body="")

    # Browser layer header
    ax.text(5.5, 2.35, "Browser Automation Layer", ha="center", va="center",
            fontsize=12, fontweight="bold", color=PALETTE["text_light"], zorder=3)

    # Three backend boxes inside browser layer
    backends = [
        (1.0, 1.2, 2.8, 0.8, "Playwright\n(browser-use)"),
        (4.3, 1.2, 2.8, 0.8, "Agent-Browser\n(Node.js sidecar)"),
        (7.6, 1.2, 2.8, 0.8, "OpenBrowser\n(Rust REST API)"),
    ]
    for bx, by, bw, bh, btext in backends:
        inner = FancyBboxPatch(
            (bx, by), bw, bh,
            boxstyle="round,pad=0.08",
            facecolor="#E74C3C", edgecolor="#C0392B",
            linewidth=0.8, alpha=0.6, zorder=3,
        )
        ax.add_patch(inner)
        ax.text(bx + bw / 2, by + bh / 2, btext, ha="center", va="center",
                fontsize=7.5, color="white", fontweight="bold", zorder=4)

    # ── Arrows ──
    _arrow(ax, 1.8, 6.85, 2.3, 6.8, label="")
    _arrow(ax, 5.1, 6.8, 5.7, 6.8, label="planning", color=PALETTE["llm"])
    _arrow(ax, 3.7, 6.3, 3.7, 5.8, label="plan", color=PALETTE["agent"])
    _arrow(ax, 2.3, 5.15, 1.8, 5.15, label="learn/heal", color=PALETTE["skills"])
    _arrow(ax, 5.1, 5.15, 5.7, 5.1, label="delegate", color=PALETTE["subagent"])
    _arrow(ax, 5.1, 4.8, 8.2, 5.3, label="store/retrieve", color=PALETTE["memory"], rad=0.1)
    _arrow(ax, 8.2, 5.8, 5.1, 5.6, label="context", color=PALETTE["memory"], rad=0.1)
    _arrow(ax, 1.8, 3.5, 2.5, 2.7, label="", color=PALETTE["skills"])
    _arrow(ax, 3.7, 4.5, 3.7, 2.7, label="execute", color=PALETTE["browser"])
    _arrow(ax, 5.7, 4.3, 5.0, 2.7, label="", color=PALETTE["subagent"])

    # ── Legend ──
    legend_items = [
        (PALETTE["manager"],  "Orchestration"),
        (PALETTE["skills"],   "Skill System"),
        (PALETTE["memory"],   "Memory"),
        (PALETTE["browser"],  "Browser"),
        (PALETTE["subagent"], "Subagents"),
        (PALETTE["llm"],      "LLM"),
    ]
    for i, (c, t) in enumerate(legend_items):
        x_leg = 8.5 + (i % 3) * 0.9
        y_leg = 0.7 - (i // 3) * 0.25
        ax.add_patch(FancyBboxPatch(
            (x_leg - 0.08, y_leg - 0.06), 0.16, 0.16,
            boxstyle="round,pad=0.02", facecolor=c, edgecolor="none", alpha=0.9,
        ))
        ax.text(x_leg + 0.15, y_leg + 0.02, t, fontsize=6.5, va="center", color=PALETTE["text_dark"])

    plt.tight_layout(pad=0.3)
    fig.savefig(FIGURES_DIR / "architecture.pdf", bbox_inches="tight", dpi=200)
    fig.savefig(FIGURES_DIR / "architecture.png", bbox_inches="tight", dpi=200)
    plt.close(fig)
    print(f"Architecture diagram saved ({FIGURES_DIR / 'architecture.pdf'})")


def draw_skill_lifecycle():
    fig, ax = plt.subplots(1, 1, figsize=(11, 4.0))
    ax.set_xlim(-0.2, 11.2)
    ax.set_ylim(-0.5, 3.8)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    stages = [
        {"x": 0.3, "w": 1.8, "color": "#27AE60", "title": "1. Record", "body": "Capture trajectory\n(actions + screenshots + DOM)"},
        {"x": 2.5, "w": 1.8, "color": "#2980B9", "title": "2. Extract", "body": "LLM review + 3-cycle\niterative refinement"},
        {"x": 4.7, "w": 1.8, "color": "#E67E22", "title": "3. Execute", "body": "Programmatic or LLM-\ndriven browser automation"},
        {"x": 6.9, "w": 1.8, "color": "#16A085", "title": "4. Self-Heal", "body": "Screenshot + DOM analysis\n→ auto-patch steps"},
        {"x": 9.1, "w": 1.8, "color": "#8E44AD", "title": "5. Audit", "body": "Staleness detection\n→ archive / prune"},
    ]

    for s in stages:
        _box(ax, s["x"], 0.8, s["w"], 2.2, s["color"],
             title=s["title"], body=s["body"],
             title_font={"fontsize": 10, "fontweight": "bold", "color": "white"},
             body_font={"fontsize": 7.5, "fontweight": "normal", "color": "white"})

    # Forward arrows between stages
    for i in range(len(stages) - 1):
        x1 = stages[i]["x"] + stages[i]["w"]
        x2 = stages[i + 1]["x"]
        _arrow(ax, x1, 1.9, x2, 1.9, color="#566573", lw=2.0)

    # Feedback loop: Self-Heal → Execute (top arc)
    ax.annotate(
        "", xy=(5.6, 3.0), xytext=(7.8, 3.0),
        arrowprops=dict(
            arrowstyle="-|>", color="#16A085", lw=1.8,
            connectionstyle="arc3,rad=-0.4", shrinkA=4, shrinkB=4,
        ),
        zorder=4,
    )
    ax.text(6.7, 3.65, "retry with healed steps", ha="center", va="center",
            fontsize=7, color="#16A085", fontstyle="italic")

    # Feedback loop: Audit → Record (bottom arc)
    ax.annotate(
        "", xy=(1.2, 0.5), xytext=(10.0, 0.5),
        arrowprops=dict(
            arrowstyle="-|>", color="#8E44AD", lw=1.8,
            connectionstyle="arc3,rad=-0.35", shrinkA=4, shrinkB=4,
        ),
        zorder=4,
    )
    ax.text(5.6, -0.2, "refresh stale skills from new trajectories", ha="center", va="center",
            fontsize=7, color="#8E44AD", fontstyle="italic")

    ax.text(5.6, 3.75, "Skill Lifecycle: Continuous Improvement Loop",
            ha="center", va="center", fontsize=12, fontweight="bold", color=PALETTE["text_dark"])

    plt.tight_layout(pad=0.3)
    fig.savefig(FIGURES_DIR / "skill_lifecycle.pdf", bbox_inches="tight", dpi=200)
    fig.savefig(FIGURES_DIR / "skill_lifecycle.png", bbox_inches="tight", dpi=200)
    plt.close(fig)
    print(f"Skill lifecycle diagram saved ({FIGURES_DIR / 'skill_lifecycle.pdf'})")


if __name__ == "__main__":
    draw_architecture()
    draw_skill_lifecycle()
