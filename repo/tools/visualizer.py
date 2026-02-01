import pandas as pd
import matplotlib.pyplot as plt
import sys
import os

def visualize_resonance(csv_path):
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return

    # Load data
    df = pd.read_csv(csv_path)
    if df.empty:
        print("Error: CSV is empty.")
        return

    print(f"Loaded {len(df)} resonance points. Generating plots...")

    # 1. Event Timeline (Density)
    plt.figure(figsize=(12, 4))
    event_counts = df.groupby('cycle').size()
    plt.bar(event_counts.index, event_counts.values, color='gray', alpha=0.6)
    plt.title("Event Density Timeline")
    plt.xlabel("Cycle")
    plt.ylabel("Num Events")
    plt.tight_layout()
    plt.savefig("event_timeline.png")
    print("Saved event_timeline.png")

    # 2. State-Timeline (Heatmap)
    plt.figure(figsize=(12, 6))
    pivot_df = df.pivot(index='state_id', columns='cycle', values='value').fillna(0)
    im = plt.pcolormesh(pivot_df.columns, pivot_df.index, pivot_df.values, cmap="YlGnBu", shading='auto')
    plt.colorbar(im, label='Resonance Value')
    plt.title("State-Timeline (Resonance)")
    plt.xlabel("Cycle")
    plt.ylabel("State ID")
    plt.tight_layout()
    plt.savefig("state_timeline.png")
    print("Saved state_timeline.png")

    # 3. Resonance Verlauf (Global/Total)
    plt.figure(figsize=(12, 4))
    global_res = df.groupby('cycle')['value'].sum()
    plt.plot(global_res.index, global_res.values, color='red', linewidth=1.5)
    plt.axhline(y=0.5, color='black', linestyle='--', alpha=0.5, label='Threshold')
    plt.title("Resonance Curve (Global Significance)")
    plt.xlabel("Cycle")
    plt.ylabel("Total Resonance")
    plt.legend()
    plt.tight_layout()
    plt.savefig("resonance_curve.png")
    print("Saved resonance_curve.png")

    # 4. State Persistence
    plt.figure(figsize=(12, 6))
    for state_id in df['state_id'].unique():
        state_data = df[df['state_id'] == state_id]
        plt.plot(state_data['cycle'], state_data['value'], label=f"State {state_id}", marker='o', markersize=2, linewidth=0.5)
    
    plt.title("State Persistence (Individual)")
    plt.xlabel("Cycle")
    plt.ylabel("Resonance")
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize='small', ncol=2)
    plt.tight_layout()
    plt.savefig("persistence_chart.png")
    print("Saved persistence_chart.png")

if __name__ == "__main__":
    csv_file = "resonance_log.csv"
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    
    try:
        visualize_resonance(csv_file)
    except ImportError as e:
        print(f"Missing dependencies: {e}. Please install pandas, matplotlib, and seaborn.")
