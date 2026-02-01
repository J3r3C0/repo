import matplotlib.pyplot as plt

def plot_resonance(events, threshold=0.6, output_path="viz_resonance.png"):
    r = [e["resonance"] for e in events]
    plt.figure(figsize=(10, 5))
    plt.plot(r, color='red', label='Resonance')
    plt.axhline(threshold, color='black', linestyle='--', label='Threshold')
    plt.fill_between(range(len(r)), r, threshold, where=(tuple(val > threshold for val in r)), color='red', alpha=0.3)
    plt.title("Resonance Significance Curve")
    plt.xlabel("Step")
    plt.ylabel("Value")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path)
    print(f"[VIZ] Saved {output_path}")
