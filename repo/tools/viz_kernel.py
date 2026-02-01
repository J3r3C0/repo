import pandas as pd
import matplotlib.pyplot as plt
import os
from pathlib import Path

def visualize_resonance(log_path="logs/resonance_log.csv"):
    """
    Sheratan Strang B: Visualization
    Generates a resonance landscape from the perception logs.
    """
    if not os.path.exists(log_path):
        print(f"Log not found: {log_path}")
        return

    df = pd.read_csv(log_path)
    if df.empty:
        print("Log is empty.")
        return

    # 1. Resonance Curve (Global Intensity)
    plt.figure(figsize=(12, 6))
    intensity = df.groupby('cycle')['resonance'].sum()
    plt.plot(intensity.index, intensity.values, color='cyan', linewidth=2, label='Global Resonance')
    plt.fill_between(intensity.index, intensity.values, color='cyan', alpha=0.1)
    
    plt.title("Sheratan Perception Intensity (Global Resonance)", color='white', fontsize=14)
    plt.xlabel("Cycle", color='gray')
    plt.ylabel("Intensity", color='gray')
    plt.grid(True, linestyle='--', alpha=0.2)
    plt.legend()
    
    # Styling for dark mode
    plt.gcf().patch.set_facecolor('#0a0a0a')
    plt.gca().set_facecolor('#0a0a0a')
    plt.gca().tick_params(colors='gray')
    
    for spine in plt.gca().spines.values():
        spine.set_color('#333333')

    out_path = "viz_kernel.png"
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    print(f"Visualization saved to {out_path}")

    # 2. Segment Heatmap (Timeline)
    plt.figure(figsize=(14, 8))
    pivot = df.pivot(index='segment', columns='cycle', values='resonance').fillna(0)
    plt.imshow(pivot, aspect='auto', cmap='magma', interpolation='nearest')
    plt.colorbar(label='Resonance Value')
    plt.title("Resonance Landscape (Segments over Time)", color='white', fontsize=14)
    plt.xlabel("Cycle", color='gray')
    plt.ylabel("Segment ID", color='gray')
    
    plt.gcf().patch.set_facecolor('#0a0a0a')
    plt.savefig("viz_landscape.png", dpi=300, bbox_inches='tight')
    print(f"Landscape saved to viz_landscape.png")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", default="logs/resonance_log.csv")
    args = parser.parse_args()
    
    # Try to import pandas/matplotlib, skip if missing
    try:
        visualize_resonance(args.log)
    except ImportError:
        print("Skipping visualization: pandas/matplotlib not installed.")
