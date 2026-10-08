# 5v5 游戏组队匹配算法

本项目实现一个简化的 LOL 组队匹配器：从等待队列中选择 TOP、JUN、MID、ADC、SUP 各一名玩家，组成一支五人队伍。本题不考虑两支队伍之间的对战平衡。

## 优化目标

对每个合法五人组合计算两个指标：

1. 平均排队时间：五名玩家等待秒数的平均值。
2. 平均分差：五名玩家两两之间排名分绝对差的平均值，共有 C(5,2)=10 对。

两个指标先进行 Min-Max 归一化，再计算加权目标：

    objective = queue_weight * normalized_queue_time
              + score_gap_weight * normalized_score_gap

目标值越小越好，默认两个权重均为 0.5。题目要求最小化平均排队时间，程序默认严格采用该定义；实际游戏可将 wait_objective 设置为 maximize，优先照顾等待较久的玩家。

## 算法流程

1. 按五个位置将玩家分组。
2. 每个位置保留至多 candidate_limit_per_role 名候选人。
3. 使用笛卡尔积生成每个位置各一人的合法组合。
4. 计算每个组合的平均排队时间和平均两两分差。
5. 归一化指标并选择加权目标最小的组合。

每个位置最多保留 k 人时，最多检查 k^5 个组合。默认 k=8，即最多 32768 个组合。

## 运行

需要 Python 3.10 或更高版本，无第三方依赖。

    python matchmaking.py

## 测试

    python -m unittest -v

## 文件说明

- matchmaking.py：核心算法和演示程序。
- test_matchmaking.py：单元测试。
- 5v5-matchmaking.md：算法设计报告。

本地原有的 simple rrm.py 是“选择 10 人并分成两队”的旧方案，与本题要求不一致，因此通过 .gitignore 保留在本地但不纳入提交。
