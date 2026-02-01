import json

class Recorder:
    def __init__(self):
        self.events = []

    def record(self, event, resonance, state_id):
        self.events.append({
            "t": event.t,
            "source": event.source,
            "resonance": resonance,
            "state_id": state_id,
            "data": str(event.data)
        })

    def save(self, path):
        with open(path, "w") as f:
            json.dump(self.events, f, indent=2)
        print(f"[RECORDER] Run saved to {path}")
