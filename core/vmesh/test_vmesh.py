# core/vmesh/test_vmesh.py
import asyncio
import unittest
from core.vmesh.stability import StabilityEvaluator, VMeshState
from core.vmesh.complexity import ComplexityTracker
from core.vmesh.sync import SynchronizationLayer, ReferenceState
from core.vmesh.controller import VMeshController, PolicyMode
from core.vmesh.robustness import RobustnessHarness

class TestVMeshLifecycle(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.evaluator = StabilityEvaluator()
        self.complexity = ComplexityTracker()
        self.sync = SynchronizationLayer(ReferenceState(policy_hash="v1"))
        self.controller = VMeshController(self.evaluator, self.complexity, self.sync)
        self.harness = RobustnessHarness(self.evaluator)

    async def test_stability_to_mode_transition(self):
        """Baseline: System is NORMAL."""
        state = VMeshState(latency_p95_ms=100, error_rate=0.0, queue_age_p95_sec=10)
        self.evaluator.evaluate(state)
        mode = self.controller.decide_mode(state)
        self.assertEqual(mode, PolicyMode.NORMAL)
        print(f"Baseline Mode: {mode}")

        """Scenario 1: Load Spike -> THROTTLE."""
        spike_state = VMeshState(latency_p95_ms=3000, error_rate=0.02, queue_age_p95_sec=50)
        self.evaluator.evaluate(spike_state)
        mode = self.controller.decide_mode(spike_state)
        self.assertEqual(mode, PolicyMode.THROTTLE)
        print(f"Spike Mode: {mode} (S={self.evaluator._last_score:.2f})")

        """Scenario 2: Critical Error -> SAFE_MODE."""
        critical_state = VMeshState(latency_p95_ms=10000, error_rate=0.6, queue_age_p95_sec=1000)
        self.evaluator.evaluate(critical_state)
        mode = self.controller.decide_mode(critical_state)
        self.assertEqual(mode, PolicyMode.SAFE_MODE)
        print(f"Critical Mode: {mode} (S={self.evaluator._last_score:.2f})")

    async def test_robustness_harness(self):
        """Test Chaos Injection."""
        async def mock_disturbance():
            # Simulate impact in evaluator
            bad_state = VMeshState(latency_p95_ms=4000, error_rate=0.2)
            self.evaluator.evaluate(bad_state)
            
        report = await self.harness.run_chaos_profile("Latency Injection", mock_disturbance)
        self.assertGreater(report["sensitivity"], 0)
        print(f"Chaos Report: {report}")

    async def test_complexity_gate(self):
        """Test 'Verbessern = Entfernen'."""
        # Case 1: More complexity, but lower stability (FAIL)
        ok = self.complexity.evaluate_change(delta_s=-0.1, delta_c=50.0)
        self.assertFalse(ok)
        
        # Case 2: More complexity, much higher stability (PASS)
        ok = self.complexity.evaluate_change(delta_s=0.2, delta_c=10.0)
        self.assertTrue(ok)

if __name__ == "__main__":
    unittest.main()
