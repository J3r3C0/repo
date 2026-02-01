import time
import requests
import json

class DummyAgent:
    """
    Minimal Agent that couples with Sheratan perception.
    """
    def __init__(self, observer_url="http://127.0.0.1:8000"):
        self.observer_url = observer_url
        self.last_dominants = set()

    def step(self):
        """
        One observation cycle for the agent.
        """
        try:
            # 1. Query current meaningful states from Sheratan Identity Layer
            response = requests.get(f"{self.observer_url}/identity?top_k=3")
            if response.status_code == 200:
                dominants = response.json()
                current_ids = {d["state_id"] for d in dominants}
                
                # 2. Detect significance (Change in dominants)
                if current_ids != self.last_dominants:
                    new = current_ids - self.last_dominants
                    lost = self.last_dominants - current_ids
                    
                    print(f"[AGENT] Perception Shift!")
                    if new: print(f"  + New significant states: {new}")
                    if lost: print(f"  - Lost significance: {lost}")
                    
                    self.last_dominants = current_ids
                    self.perform_action(dominants)
            else:
                print(f"[AGENT] Error: Observer unreachable ({response.status_code})")
        except Exception as e:
            print(f"[AGENT] Connection error: {e}")

    def perform_action(self, dominants):
        """
        Dummy action based on perception.
        """
        if any(d["value"] > 5.0 for d in dominants):
            print("[AGENT] ACTION: Critical Resonance Detected! Triggering high-priority reflex.")
        else:
            print("[AGENT] ACTION: Monitoring stable state.")

if __name__ == "__main__":
    # To test: Ensure api_observer.py is running
    agent = DummyAgent()
    print("[AGENT] Started. Waiting for perception signals...")
    while True:
        agent.step()
        time.sleep(2)
