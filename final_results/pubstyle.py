"""Shared publication style for the final figures (scientific-journal look).

Conventions: no figure/axes titles (captions go in the manuscript), serif text, small fonts,
thin spines, embedded TrueType fonts in the PDF, 300 dpi, tight bounding box.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def apply():
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "font.size": 9,
        "axes.titlesize": 9,        # titles are not used; kept for safety
        "axes.labelsize": 9,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 8,
        "legend.frameon": False,
        "axes.linewidth": 0.7,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.major.width": 0.7,
        "ytick.major.width": 0.7,
        "lines.linewidth": 1.3,
        "lines.markersize": 5,
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })


# consistent palette (colour-blind friendly)
MODEL_COLOR = {
    "gpt-oss-20b": "#4C72B0",
    "Qwen3-Coder-30B-A3B": "#DD8452",
    "Qwen3-Coder-Next": "#55A868",
    "Qwen3-32B": "#C44E52",
    "Kimi-Dev-72B": "#8172B2",
}
GPU_COLOR = {"A100": "#C44E52", "H100": "#4C72B0", "H200": "#55A868"}
COMMERCIAL_COLOR = {"GPT-5.4": "#55A868", "Opus 4.8": "#4C72B0", "Gemini 3.1 Pro": "#C44E52"}


def save(fig, path_noext):
    fig.savefig(f"{path_noext}.pdf")
    fig.savefig(f"{path_noext}.png", dpi=300)
