"""
Analyze benchmark results and generate figures for the paper.
"""

import json
import os
from pathlib import Path
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

RESULTS_DIR = Path(__file__).resolve().parent.parent.parent / "benchmarks" / "skill_generalization" / "results"
FIGURES_DIR = Path(__file__).resolve().parent.parent / "figures"


def load_all_results():
    results = []
    for f in sorted(RESULTS_DIR.glob("*.jsonl")):
        with open(f) as fp:
            for line in fp:
                line = line.strip()
                if line:
                    results.append(json.loads(line))
    return results


def summarize(results):
    print(f"Total results: {len(results)}")

    by_mode = defaultdict(lambda: {"total": 0, "success": 0, "scores": [], "times": [], "tokens": []})
    by_task = defaultdict(lambda: defaultdict(lambda: {"total": 0, "success": 0, "scores": []}))

    for r in results:
        mode = r.get("mode", "?")
        task_id = r.get("task_id", "?")
        by_mode[mode]["total"] += 1
        if r.get("success"):
            by_mode[mode]["success"] += 1
        by_mode[mode]["scores"].append(r.get("score", 0))
        by_mode[mode]["times"].append(r.get("time_seconds", 0))

        by_task[mode][task_id]["total"] += 1
        if r.get("success"):
            by_task[mode][task_id]["success"] += 1
        by_task[mode][task_id]["scores"].append(r.get("score", 0))

    # Print summary
    print("\n=== Results by Mode ===")
    for mode, stats in by_mode.items():
        n = stats["total"]
        s = stats["success"]
        avg_score = np.mean(stats["scores"]) if stats["scores"] else 0
        avg_time = np.mean(stats["times"]) if stats["times"] else 0
        print(f"  {mode}: {s}/{n} success ({100*s/n:.1f}%), avg score={avg_score:.3f}, avg time={avg_time:.1f}s")

    print("\n=== Results by Task ===")
    for mode, tasks in by_task.items():
        for tid, stats in tasks.items():
            n = stats["total"]
            s = stats["success"]
            print(f"  [{mode}] {tid}: {s}/{n} success ({100*s/n:.1f}%)")

    return by_mode, by_task


def generate_figures(results, by_mode):
    os.makedirs(FIGURES_DIR, exist_ok=True)

    # --- Figure 1: Success rate comparison ---
    modes = list(by_mode.keys())
    success_rates = [by_mode[m]["success"] / by_mode[m]["total"] * 100 for m in modes]
    counts = [by_mode[m]["total"] for m in modes]

    fig, ax = plt.subplots(figsize=(5, 3.5))
    bars = ax.bar(modes, success_rates, color=["#2ecc71", "#e74c3c"], edgecolor="black", linewidth=0.8)
    for bar, rate, count in zip(bars, success_rates, counts):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                f"{rate:.1f}%\n(n={count})", ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax.set_ylabel("Success Rate (%)")
    ax.set_title("Success Rate on Evil Skill Generalization Benchmark")
    ax.set_ylim(0, max(success_rates) * 1.4 + 5)
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    fig.savefig(FIGURES_DIR / "success_rate.pdf", bbox_inches="tight")
    plt.close(fig)

    # --- Figure 2: Score distribution ---
    fig, ax = plt.subplots(figsize=(5, 3.5))
    for i, mode in enumerate(modes):
        scores = by_mode[mode]["scores"]
        ax.hist(scores, bins=8, alpha=0.6, label=mode, range=(0, 1))
    ax.set_xlabel("Score")
    ax.set_ylabel("Count")
    ax.set_title("Score Distribution by Mode")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    fig.savefig(FIGURES_DIR / "score_distribution.pdf", bbox_inches="tight")
    plt.close(fig)

    # --- Figure 3: Time comparison ---
    fig, ax = plt.subplots(figsize=(5, 3.5))
    data = [by_mode[m]["times"] for m in modes]
    bp = ax.boxplot(data, labels=modes, patch_artist=True)
    for patch, color in zip(bp["boxes"], ["#2ecc71", "#e74c3c"]):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)
    ax.set_ylabel("Time (seconds)")
    ax.set_title("Task Completion Time by Mode")
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    fig.savefig(FIGURES_DIR / "time_comparison.pdf", bbox_inches="tight")
    plt.close(fig)

    # --- Figure 4: Task-level breakdown ---
    all_tasks = sorted(set(r["task_id"] for r in results))
    task_labels = [t.replace("_", "\\_") for t in all_tasks]

    fig, ax = plt.subplots(figsize=(7, 3.5))
    x = np.arange(len(all_tasks))
    width = 0.35
    for i, mode in enumerate(modes):
        mode_results = [r for r in results if r["mode"] == mode]
        task_scores = defaultdict(list)
        for r in mode_results:
            task_scores[r["task_id"]].append(r["score"])
        avg_scores = [np.mean(task_scores.get(t, [0])) for t in all_tasks]
        ax.bar(x + i * width, avg_scores, width, label=mode, alpha=0.8)
    ax.set_ylabel("Average Score")
    ax.set_title("Per-Task Average Score")
    ax.set_xticks(x + width / 2)
    ax.set_xticklabels(task_labels, rotation=30, ha="right", fontsize=8)
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    fig.savefig(FIGURES_DIR / "task_breakdown.pdf", bbox_inches="tight")
    plt.close(fig)

    print(f"\nFigures saved to {FIGURES_DIR}/")


if __name__ == "__main__":
    results = load_all_results()
    by_mode, by_task = summarize(results)
    generate_figures(results, by_mode)
