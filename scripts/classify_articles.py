"""Deterministic topic classification from article metadata, without API costs."""
import re

TOPICS = {
    "Backend": [r"\bspring\b", r"\bjava\b", r"\bnode\.?js\b", r"\bapi\b", "백엔드", "서버 개발"],
    "Frontend": [r"\breact\b", r"\bvue\b", r"\btypescript\b", r"\bcss\b", "프론트엔드"],
    "Database": [r"\bpostgres(?:ql)?\b", r"\bmysql\b", r"\bredis\b", r"\bsql\b", "데이터베이스"],
    "Infrastructure": [r"\bkubernetes\b", r"\bdocker\b", r"\bterraform\b", r"\baws\b", "인프라"],
    "AI/ML": [r"\bllm\b", r"\brag\b", r"\bmachine learning\b", "인공지능", "머신러닝"],
    "Security": [r"\boauth\b", r"\bjwt\b", r"\bxss\b", "보안", "인증", "취약점"],
    "Architecture": [r"\bmicroservices?\b", r"\bddd\b", r"\bmsa\b", "아키텍처", "분산 시스템"],
    "Engineering": [r"\bincident\b", r"\bpostmortem\b", r"\bperformance\b", "장애", "성능", "최적화", "회고"],
}
TYPES = {
    "troubleshooting": [r"\bincident\b", r"\bpostmortem\b", "장애", "오류", "트러블슈팅", "문제 해결"],
    "comparison": [r"\bvs\.?\b", r"\bcomparison\b", "비교", "장단점"],
    "tutorial": [r"\bhow to\b", r"\btutorial\b", "가이드", "시작하기", "따라하기"],
}
def classify(article):
    text = " ".join([article.get("title") or "", article.get("summary") or ""]).lower()
    topics = [name for name, patterns in TOPICS.items() if any(re.search(p, text, re.IGNORECASE) for p in patterns)]
    kinds = [name for name, patterns in TYPES.items() if any(re.search(p, text, re.IGNORECASE) for p in patterns)]
    return {"topics": topics, "content_type": kinds[0] if kinds else "general", "classification_method": "rules-v1"}
