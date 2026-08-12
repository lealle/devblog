"""
실패한 피드를 feeds.json 에서 지운다.

data/feed_state.json 의 fail_count 를 보고 기준치 이상인 것을 제거하며,
지우기 전 목록을 data/removed_feeds.json 에 남겨 둔다.

    python scripts/prune_feeds.py          # fail_count >= 2 인 피드 제거
    python scripts/prune_feeds.py 3        # 기준을 3 으로
"""
import json
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"


def main() -> int:
    threshold = int(sys.argv[1]) if len(sys.argv) > 1 else 2

    feeds_path = DATA / "feeds.json"
    state_path = DATA / "feed_state.json"

    feeds = json.loads(feeds_path.read_text(encoding="utf-8"))
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}

    keep, drop = [], []
    for f in feeds:
        st = state.get(f["feed_url"], {})
        if st.get("fail_count", 0) >= threshold:
            drop.append({**f, "reason": st.get("last_error") or st.get("last_status")})
        else:
            keep.append(f)

    if not drop:
        print("지울 피드가 없습니다.")
        return 0

    # 지운 목록을 남겨 둔다. 나중에 주소를 고쳐 되살릴 수 있다.
    removed_path = DATA / "removed_feeds.json"
    previous = []
    if removed_path.exists():
        previous = json.loads(removed_path.read_text(encoding="utf-8"))
    removed_path.write_text(
        json.dumps(previous + drop, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )

    # 지운 피드의 상태 기록도 정리
    dropped_urls = {f["feed_url"] for f in drop}
    state = {k: v for k, v in state.items() if k not in dropped_urls}
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=1) + "\n",
                          encoding="utf-8")

    feeds_path.write_text(json.dumps(keep, ensure_ascii=False, indent=1) + "\n",
                          encoding="utf-8")

    by_reason = {}
    for f in drop:
        by_reason.setdefault(str(f["reason"]), []).append(f["name"])

    print(f"{len(drop)}개 제거 (남은 피드 {len(keep)}개)")
    for reason, names in sorted(by_reason.items(), key=lambda x: -len(x[1])):
        print(f"  {reason}: {len(names)}개 - {', '.join(names[:5])}"
              + (" ..." if len(names) > 5 else ""))
    print(f"\n제거 목록은 data/removed_feeds.json 에 남겨 두었습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
