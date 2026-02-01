import numpy as np
import random
from core.events import create_event_buffer

def generate_meaningful_scenario(num_cycles=100, num_channels=5):
    """
    Generates a series of events across multiple cycles.
    Includes persistent 'meaningful' signals and random noise.
    """
    all_events = []
    
    # Define meaningful patterns: (channel, base_value, frequency)
    patterns = [
        (1, 0.7, 0.2), # Channel 1: High value, recurring 20% of the time
        (2, 0.4, 0.8), # Channel 2: Medium value, very frequent
        (3, 0.9, 0.05),# Channel 3: Very high value, very rare
    ]
    
    event_id = 0
    for cycle in range(num_cycles):
        cycle_events = []
        
        # 1. Generate Signal from patterns
        for channel, base_val, freq in patterns:
            if random.random() < freq:
                # Add some variance to the value
                val = base_val + (random.random() - 0.5) * 0.1
                cycle_events.append((event_id, val, cycle * 10, channel))
                event_id += 1
                
        # 2. Generate Noise
        num_noise = random.randint(0, 3)
        for _ in range(num_noise):
            val = random.random() * 0.3 # Low value resonance
            channel = random.randint(1, num_channels)
            cycle_events.append((event_id, val, cycle * 10, channel))
            event_id += 1
            
        all_events.append(create_event_buffer(cycle_events))
        
    return all_events

if __name__ == "__main__":
    scenario = generate_meaningful_scenario(5)
    for i, events in enumerate(scenario):
        print(f"Cycle {i}: {len(events)} events generated.")
        if len(events) > 0:
            print(f"  First Event: {events[0]}")
