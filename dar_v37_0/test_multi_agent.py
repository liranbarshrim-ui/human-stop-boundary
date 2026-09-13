import unittest

from multi_agent import (
    DARMAError,
    Delegation,
    MultiAgentBoundary,
    OutcomeContract,
    OutcomeEdge,
    OutcomeGraph,
)


class MultiAgentTests(unittest.TestCase):
    def setUp(self):
        self.b = MultiAgentBoundary({
            "transfer": OutcomeContract("transfer", "finance", "alice"),
        })

    def test_named_authority_can_stop_and_stop_is_persistent(self):
        self.assertTrue(self.b.can_execute("alice", "transfer", 0))
        stop = self.b.stop("alice", "transfer", "human refusal")
        self.assertEqual(stop.epoch, 1)
        self.assertFalse(self.b.can_execute("alice", "transfer", 1))
        self.assertFalse(self.b.can_execute("agent-c", "transfer", 99))

    def test_wrong_authority_cannot_stop(self):
        with self.assertRaises(PermissionError):
            self.b.stop("agent-c", "transfer")

    def test_delegation_cannot_widen(self):
        self.b.delegate("alice", "agent-a", {"transfer"}, 0)
        with self.assertRaises(PermissionError):
            self.b.delegate("agent-a", "agent-b", {"transfer", "unknown"}, 0)

    def test_delegated_authority_is_invalid_after_stop(self):
        self.b.delegate("alice", "agent-a", {"transfer"}, 0)
        self.assertTrue(self.b.can_execute("agent-a", "transfer", 0))
        self.b.stop("alice", "transfer")
        self.assertFalse(self.b.can_execute("agent-a", "transfer", 100))
        with self.assertRaises(PermissionError):
            self.b.delegate("alice", "agent-b", {"transfer"}, 2)

    def test_stop_cut_detects_alternate_distributed_path(self):
        graph = OutcomeGraph(
            frozenset({"A", "B", "C", "O"}),
            (
                OutcomeEdge("A", "B", frozenset({"transfer"}), True),
                OutcomeEdge("B", "O", frozenset({"transfer"}), False),
                OutcomeEdge("A", "C", frozenset({"transfer"}), False),
                OutcomeEdge("C", "O", frozenset({"transfer"}), False),
            ),
        )
        with self.assertRaises(DARMAError):
            self.b.verify_graph(graph, "transfer")

    def test_stop_cut_accepts_all_paths_crossing_enforcement(self):
        graph = OutcomeGraph(
            frozenset({"A", "B", "C", "O"}),
            (
                OutcomeEdge("A", "B", frozenset({"transfer"}), True),
                OutcomeEdge("B", "O", frozenset({"transfer"}), False),
                OutcomeEdge("A", "C", frozenset({"transfer"}), True),
                OutcomeEdge("C", "O", frozenset({"transfer"}), False),
            ),
        )
        self.b.verify_graph(graph, "transfer")

    def test_no_path_is_not_claimed_as_a_stop_cut(self):
        graph = OutcomeGraph(frozenset({"A", "O"}), (OutcomeEdge("A", "O"),))
        with self.assertRaises(DARMAError):
            self.b.verify_graph(graph, "transfer")


if __name__ == "__main__":
    unittest.main()
