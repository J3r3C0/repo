import matplotlib.pyplot as plt
import os

def plot_timeline(events, output_path="viz_timeline.png"):
    times = [e["t"] for e in events]
    # Simple scatter plot for event density
    plt.figure(figsize=(10, 4))
    plt.eventplot(times, orientation='horizontal', colors='k')
    plt.title("Event Timeline (Density)")
    plt.xlabel("Time (s)")
    plt.tight_layout()
    plt.savefig(output_path)
    print(f"[VIZ] Saved {output_path}")
