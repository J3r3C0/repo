import pytest
from unittest.mock import patch, MagicMock
from dummy_agent import DummyAgent

def test_agent_perception_shift():
    observer_url = "http://127.0.0.1:8000"
    agent = DummyAgent(observer_url=observer_url)
    
    # Use patch to mock requests.get
    with patch('requests.get') as mock_get:
        # 1. First response: State 1 is dominant
        mock_response_1 = MagicMock()
        mock_response_1.status_code = 200
        mock_response_1.json.return_value = [{"state_id": 1, "value": 0.8, "last_seen": 10}]
        
        # 2. Second response: State 2 is dominant
        mock_response_2 = MagicMock()
        mock_response_2.status_code = 200
        mock_response_2.json.return_value = [{"state_id": 2, "value": 0.9, "last_seen": 11}]
        
        # Configure the mock to return these responses in sequence
        mock_get.side_effect = [mock_response_1, mock_response_2]
        
        # Step 1
        agent.step()
        assert agent.last_dominants == {1}
        
        # Step 2
        agent.step()
        assert agent.last_dominants == {2}
    # verify that perform_action was (theoretically) called
    # (Checking set change is sufficient for PoC logic verification)

def test_agent_critical_resonance_action(capsys):
    agent = DummyAgent()
    
    # Dominant with value > 5.0 should trigger critical action
    dominants = [{"state_id": 1, "value": 6.0, "last_seen": 10}]
    agent.perform_action(dominants)
    
    captured = capsys.readouterr()
    assert "ACTION: Critical Resonance Detected" in captured.out
