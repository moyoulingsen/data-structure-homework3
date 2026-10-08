"""基于排队时间和排名分差的五位置组队匹配算法。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from itertools import combinations, product
from statistics import fmean
from typing import Iterable, Literal, Sequence


class Role(str, Enum):
    TOP = "top"
    JUN = "jun"
    MID = "mid"
    ADC = "adc"
    SUP = "sup"


ROLE_ORDER = (Role.TOP, Role.JUN, Role.MID, Role.ADC, Role.SUP)


@dataclass(frozen=True, slots=True)
class Player:
    player_id: str
    role: Role
    ranking_score: float
    requested_at: datetime


@dataclass(frozen=True, slots=True)
class TeamMetrics:
    average_queue_seconds: float
    average_score_gap: float
    score_range: float


@dataclass(frozen=True, slots=True)
class MatchResult:
    players: tuple[Player, ...]
    metrics: TeamMetrics
    objective_score: float


class MatchmakingError(ValueError):
    """无法组成合法的五位置队伍时抛出的异常。"""


class Matchmaker:
    """从每个位置选择一名玩家，并最小化归一化后的加权目标。"""

    def __init__(
        self,
        *,
        queue_weight: float = 0.5,
        score_gap_weight: float = 0.5,
        candidate_limit_per_role: int = 8,
        wait_objective: Literal["minimize", "maximize"] = "minimize",
    ) -> None:
        if queue_weight < 0 or score_gap_weight < 0:
            raise ValueError("目标权重不能为负数")
        if queue_weight + score_gap_weight == 0:
            raise ValueError("至少一个目标权重必须大于零")
        if candidate_limit_per_role < 1:
            raise ValueError("每个位置的候选人数上限必须大于零")
        if wait_objective not in {"minimize", "maximize"}:
            raise ValueError("排队目标只能是 minimize 或 maximize")

        total_weight = queue_weight + score_gap_weight
        self.queue_weight = queue_weight / total_weight
        self.score_gap_weight = score_gap_weight / total_weight
        self.candidate_limit_per_role = candidate_limit_per_role
        self.wait_objective = wait_objective

    def find_best_team(
        self,
        players: Iterable[Player],
        *,
        now: datetime | None = None,
    ) -> MatchResult:
        now = now or datetime.now(timezone.utc)
        grouped = self._group_candidates(players)
        missing_roles = [role.value for role in ROLE_ORDER if not grouped[role]]
        if missing_roles:
            raise MatchmakingError(
                "无法组成队伍，缺少位置：" + ", ".join(missing_roles)
            )

        # 使用笛卡尔积生成每个位置各一人的所有合法组合。
        evaluated = [
            (team, calculate_metrics(team, now=now))
            for team in product(*(grouped[role] for role in ROLE_ORDER))
        ]
        queue_values = [metrics.average_queue_seconds for _, metrics in evaluated]
        gap_values = [metrics.average_score_gap for _, metrics in evaluated]
        queue_min, queue_max = min(queue_values), max(queue_values)
        gap_min, gap_max = min(gap_values), max(gap_values)

        def objective(item: tuple[tuple[Player, ...], TeamMetrics]) -> tuple:
            team, metrics = item
            # 两个指标量纲不同，先归一化到 [0, 1] 再加权。
            normalized_queue = _normalize(
                metrics.average_queue_seconds, queue_min, queue_max
            )
            # 题目要求最小化等待时间；实际系统也可以配置为优先等待更久者。
            if self.wait_objective == "maximize":
                normalized_queue = 1.0 - normalized_queue
            normalized_gap = _normalize(metrics.average_score_gap, gap_min, gap_max)
            weighted_score = (
                self.queue_weight * normalized_queue
                + self.score_gap_weight * normalized_gap
            )
            queue_tiebreaker = metrics.average_queue_seconds
            if self.wait_objective == "maximize":
                queue_tiebreaker = -queue_tiebreaker
            return (
                weighted_score,
                metrics.average_score_gap,
                metrics.score_range,
                queue_tiebreaker,
                *(player.player_id for player in team),
            )

        best_team, best_metrics = min(evaluated, key=objective)
        return MatchResult(
            best_team,
            best_metrics,
            objective((best_team, best_metrics))[0],
        )

    def _group_candidates(self, players: Iterable[Player]) -> dict[Role, list[Player]]:
        grouped = {role: [] for role in ROLE_ORDER}
        for player in players:
            grouped[player.role].append(player)

        newest_first = self.wait_objective == "minimize"
        for role in ROLE_ORDER:
            grouped[role].sort(
                key=lambda player: (player.requested_at, player.player_id),
                reverse=newest_first,
            )
            grouped[role] = grouped[role][: self.candidate_limit_per_role]
        return grouped


def calculate_metrics(team: Sequence[Player], *, now: datetime) -> TeamMetrics:
    if len(team) != len(ROLE_ORDER):
        raise ValueError("一支队伍必须恰好包含五名玩家")
    if {player.role for player in team} != set(ROLE_ORDER):
        raise ValueError("一支队伍必须包含五个不同位置的玩家")

    queue_seconds = [
        max(0.0, (now - player.requested_at).total_seconds()) for player in team
    ]
    scores = [player.ranking_score for player in team]
    # 五名玩家共有十个不同玩家对，分差取绝对值后求平均。
    pairwise_gaps = [abs(a - b) for a, b in combinations(scores, 2)]
    return TeamMetrics(
        average_queue_seconds=fmean(queue_seconds),
        average_score_gap=fmean(pairwise_gaps),
        score_range=max(scores) - min(scores),
    )


def _normalize(value: float, minimum: float, maximum: float) -> float:
    # 所有候选值相同时，该指标不影响最终排序。
    if maximum == minimum:
        return 0.0
    return (value - minimum) / (maximum - minimum)


def demo_players(now: datetime) -> list[Player]:
    role_scores = {
        Role.TOP: (1480, 1550, 1690),
        Role.JUN: (1495, 1580, 1720),
        Role.MID: (1510, 1600, 1760),
        Role.ADC: (1500, 1570, 1710),
        Role.SUP: (1485, 1590, 1740),
    }
    players: list[Player] = []
    for role_index, role in enumerate(ROLE_ORDER):
        for player_index, score in enumerate(role_scores[role]):
            players.append(
                Player(
                    player_id=f"{role.value}-{player_index + 1}",
                    role=role,
                    ranking_score=score,
                    requested_at=now
                    - timedelta(seconds=45 + role_index * 8 + player_index * 75),
                )
            )
    return players


def main() -> None:
    now = datetime.now(timezone.utc)
    result = Matchmaker().find_best_team(demo_players(now), now=now)
    print("匹配到的队伍")
    for player in result.players:
        waited = (now - player.requested_at).total_seconds()
        print(
            f"  {player.role.value:>3}: {player.player_id:<8} "
            f"排名分={player.ranking_score:.0f} 等待={waited:.0f}秒"
        )
    print(f"平均排队时间：{result.metrics.average_queue_seconds:.2f}秒")
    print(f"平均两两分差：{result.metrics.average_score_gap:.2f}")
    print(f"排名分极差：{result.metrics.score_range:.2f}")
    print(f"归一化目标值：{result.objective_score:.4f}")


if __name__ == "__main__":
    main()
