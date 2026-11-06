"""Build the public-only design catalog for the Dev Resource Hub.

The Prompt Library and DevKit are private repositories. Never clone, copy or
publish their contents into the public DevBlog Pages artifact.

Run: python scripts/build_resource_hub.py --design-index _sources/design-atlas/docs/designs.json
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DESIGN_BASE = "https://lealle.github.io/design-atlas/designs/"
EXPERIENCE_BASE = "https://lealle.github.io/design-atlas/experiences/index.html?scene="
EXPERIENCE_NAMES = (
    "작업실", "잡지", "스크롤 필름", "지식 지도", "프롬프트 실험실", "검색",
    "가로 전시", "과정 기록", "목록/상세", "활자 포스터", "카드 덱", "독서실",
    "서랍", "티켓", "작업 보드", "노선도", "폴더 트리", "뒤집기",
    "편집 신문", "다이얼", "픽셀 데스크톱", "확장 패널", "표지", "분할 비교",
    "핀 보드", "단계 안내", "정렬 표", "방사형 메뉴", "편지", "파일 탐색기",
    "가변 지면", "주석", "체크 진행률", "요일 큐레이션", "책장", "로컬 명령",
    "분기 탐색", "장면 슬라이더", "모자이크", "대화 선택", "캔버스", "형태 연구소",
)


def load_designs(file: Path) -> list[dict]:
    """Load only explicitly public metadata. Validate IDs before URL assembly."""
    data = json.loads(file.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise ValueError("Design index must be a nonempty array")
    result: list[dict] = []
    seen: set[str] = set()
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("Invalid design entry")
        design_id = item.get("id")
        if not isinstance(design_id, str) or not re.fullmatch(r"\d{3}", design_id):
            raise ValueError(f"Invalid design id: {design_id!r}")
        if design_id in seen:
            raise ValueError(f"Duplicate design id: {design_id}")
        seen.add(design_id)
        result.append({
            "id": f"design-{design_id}",
            "kind": "design",
            "title": item.get("name") or f"디자인 {design_id}",
            "number": design_id,
            "category": item.get("layout") or "layout",
            "category_label": item.get("layoutName") or "디자인",
            "description": item.get("description") or "",
            "style": item.get("styleName") or "",
            "url": DESIGN_BASE + design_id + ".html",
        })
    return result


def load_experiences() -> list[dict]:
    return [
        {
            "id": f"experience-{number:02d}",
            "kind": "experience",
            "title": name,
            "number": f"{number:02d}",
            "category": "experience",
            "category_label": "체험형 디자인",
            "description": "직접 조작해 볼 수 있는 인터랙티브 화면",
            "url": EXPERIENCE_BASE + str(number),
        }
        for number, name in enumerate(EXPERIENCE_NAMES, 1)
    ]


def build(designs_file: Path, output: Path) -> dict:
    designs = load_designs(designs_file)
    experiences = load_experiences()
    data = {
        "schema": 2,
        "source": {"designs": "https://github.com/lealle/design-atlas"},
        "counts": {"designs": len(designs), "experiences": len(experiences)},
        "items": designs + experiences,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(serialized + "\n", encoding="utf-8")
    temporary.replace(output)
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design-index", type=Path, default=PROJECT_ROOT / "_sources/design-atlas/docs/designs.json")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "public/hub-data.json")
    args = parser.parse_args()
    data = build(args.design_index, args.output)
    print("Public-only hub index built:", data["counts"], "->", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
