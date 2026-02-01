import matplotlib.pyplot as plt
import numpy as np
from sklearn.decomposition import PCA

def plot_state_space(engine, output_path="viz_states.png"):
    if not engine.states:
        print("[VIZ] No states to plot.")
        return

    vectors = np.array([s.vector for s in engine.states])
    weights = [s.weight for s in engine.states]
    
    # Need at least 2 components for PCA, if states < 2 we just scatter
    plt.figure(figsize=(8, 8))
    if len(vectors) >= 2:
        pca = PCA(n_components=2)
        pts = pca.fit_transform(vectors)
        plt.scatter(pts[:,0], pts[:,1], s=[w*50 for w in weights], alpha=0.6, c=weights, cmap='viridis')
        plt.xlabel("PCA 1")
        plt.ylabel("PCA 2")
    else:
        plt.scatter([0]*len(vectors), vectors[:,0], s=[w*50 for w in weights], alpha=0.6)
        plt.xlabel("N/A")
        plt.ylabel("Dim 0")

    plt.title("State-Space Projection (Structural Clustering)")
    plt.tight_layout()
    plt.savefig(output_path)
    print(f"[VIZ] Saved {output_path}")
