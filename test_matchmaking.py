import unittest
from datetime import datetime, timedelta, timezone

from matchmaking import Matchmaker, MatchmakingError, Player, Role, calculate_metrics


class MatchmakingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 10, 8, 8, 0, tzinfo=timezone.utc)

    def test_metrics_use_all_ten_pairwise_score_gaps(self) -> None:
        players = [
            Player(f"p{i}", role, 1100 if role is Role.SUP else 1000, self.now)
            for i, role in enumerate(Role)
        ]
        metrics = calculate_metrics(players, now=self.now)
        self.assertEqual(metrics.average_score_gap, 40)
        self.assertEqual(metrics.score_range, 100)

    def test_result_contains_exactly_one_player_per_role(self) -> None:
        players = []
        for role_index, role in enumerate(Role):
            players.extend(
                [
                    Player(
                        f"{role.value}-balanced",
                        role,
                        1500 + role_index,
                        self.now - timedelta(minutes=5),
                    ),
                    Player(
                        f"{role.value}-fast",
                        role,
                        1000 + role_index * 500,
                        self.now - timedelta(minutes=1),
                    ),
                ]
            )
        result = Matchmaker(queue_weight=0.0, score_gap_weight=1.0).find_best_team(
            players, now=self.now
        )
        self.assertEqual({player.role for player in result.players}, set(Role))
        self.assertTrue(all("balanced" in player.player_id for player in result.players))

    def test_minimize_wait_selects_recent_players_when_scores_are_equal(self) -> None:
        players = []
        for role in Role:
            players.extend(
                [
                    Player(
                        f"{role.value}-old",
                        role,
                        1500,
                        self.now - timedelta(minutes=10),
                    ),
                    Player(
                        f"{role.value}-new",
                        role,
                        1500,
                        self.now - timedelta(minutes=1),
                    ),
                ]
            )
        result = Matchmaker().find_best_team(players, now=self.now)
        self.assertTrue(all(player.player_id.endswith("-new") for player in result.players))

    def test_missing_role_raises_clear_error(self) -> None:
        players = [Player(role.value, role, 1500, self.now) for role in list(Role)[:-1]]
        with self.assertRaisesRegex(MatchmakingError, "sup"):
            Matchmaker().find_best_team(players, now=self.now)


if __name__ == "__main__":
    unittest.main()
