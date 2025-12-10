# score.py
import json
import os

SCORE_FILE = "scores.json"
MAX_SCORES = 10

def load_scores():
    """返回列表: [{"name": "AAA", "score": 30}, ...]，按分数从大到小排序"""
    if SCORE_FILE not in os.listdir():
        return []
    try:
        with open(SCORE_FILE, "r") as f:
            data = json.load(f)
        scores = []
        for item in data:
            if isinstance(item, dict) and "name" in item and "score" in item:
                scores.append({
                    "name": item["name"],
                    "score": int(item["score"])
                })
        scores.sort(key=lambda x: x["score"], reverse=True)
        return scores[:MAX_SCORES]
    except:
        return []

def save_scores(scores):
    """写回文件前再截断为前 MAX_SCORES"""
    scores = sorted(scores, key=lambda x: x["score"], reverse=True)[:MAX_SCORES]
    with open(SCORE_FILE, "w") as f:
        json.dump(scores, f)

def add_score(name, new_score):
    """添加一条记录，然后只保留前 MAX_SCORES 名"""
    scores = load_scores()
    scores.append({"name": name, "score": int(new_score)})
    save_scores(scores)

def can_enter_leaderboard(new_score):
    """
    判断 new_score 是否有资格进入排行榜：
      - 分数 <= 0：不算
      - 现有记录少于 MAX_SCORES：一定可以
      - 否则，new_score >= 当前榜单最低分 才可以
    """
    try:
        new_score = int(new_score)
    except:
        return False

    if new_score <= 0:
        return False

    scores = load_scores()
    if len(scores) < MAX_SCORES:
        return True

    # scores 已按从大到小排序，最后一个是最低分
    min_score = scores[-1]["score"]
    return new_score >= min_score

