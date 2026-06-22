"""
fetch_jobs.py
─────────────────────────────────────────────────────────────────────
고용24(워크넷) 공식 채용정보 OpenAPI에서 '서울 · 여성/고령자 우대' 채용을 받아
index.html이 읽는 jobs.json 으로 저장합니다.

■ 실행 위치
  - GitHub Actions가 매일 자동으로 실행합니다(.github/workflows/update.yml).
  - 인증키는 GitHub 저장소의 Secret(WORK24_API_KEY)에 넣어두면 됩니다.
  - 로컬에서 직접 돌릴 수도 있습니다(아래 참고).

■ 로컬 테스트
    pip install requests
    set WORK24_API_KEY=발급받은키      (Windows)
    export WORK24_API_KEY=발급받은키   (Mac/Linux)
    python fetch_jobs.py
"""

import datetime as dt
import json
import os
import re
from pathlib import Path

API_KEY = os.environ.get("WORK24_API_KEY", "").strip()
OUTPUT = Path("jobs.json")

DISPLAY   = 100
MAX_PAGES = 5
API_URL   = "http://openapi.work.go.kr/opi/opi/opia/wantedApi.do"

# 서울 · 여성/고령자 우대 조건
# ★ region 코드, returnType, 응답 태그명은 발급 후 받는 '개발명세서'에서 확인해 맞춰 주세요.
QUERY_PARAMS = {
    "authKey": API_KEY,
    "callTp": "L",
    "returnType": "XML",
    "display": DISPLAY,
    "region": "11000",   # 서울특별시
}
FIELD_MAP = {
    "title":   ["title", "wantedTitle"],
    "company": ["company", "coNm"],
    "region":  ["region", "workRegion"],
    "sal":     ["sal", "salary"],
    "empType": ["empTpNm", "empTpCd"],
    "closeDt": ["closeDt", "wantedEndDt"],
    "url":     ["wantedInfoUrl", "wantedMobileInfoUrl", "infoUrl"],
}


def _first(elem, tags):
    for t in tags:
        n = elem.find(t)
        if n is not None and n.text:
            return n.text.strip()
    return ""


def extract_gu(region):
    m = re.search(r"([가-힣]+구)", region or "")
    return m.group(1) if m else "기타"


def fetch():
    import xml.etree.ElementTree as ET
    import requests

    rows = []
    for page in range(1, MAX_PAGES + 1):
        params = dict(QUERY_PARAMS, startPage=page)
        r = requests.get(API_URL, params=params, timeout=15)
        r.encoding = "utf-8"
        root = ET.fromstring(r.text)
        items = root.findall(".//wanted")
        if not items:
            break
        for it in items:
            region = _first(it, FIELD_MAP["region"])
            rows.append({
                "title": _first(it, FIELD_MAP["title"]),
                "co":    _first(it, FIELD_MAP["company"]),
                "gu":    extract_gu(region),
                "sal":   _first(it, FIELD_MAP["sal"]) or "회사내규",
                "type":  "시간제" if "시간" in _first(it, FIELD_MAP["empType"]) else "전일제",
                "close": _first(it, FIELD_MAP["closeDt"]),
                "url":   _first(it, FIELD_MAP["url"]) or "https://www.work24.go.kr",
            })
    seen, uniq = set(), []
    for x in rows:
        key = (x["co"], x["title"])
        if key not in seen:
            seen.add(key)
            uniq.append(x)
    return uniq


def main():
    if not API_KEY:
        print("WORK24_API_KEY가 없습니다. (Secret 미설정) 갱신을 건너뜁니다.")
        return
    print("고용24 API에서 채용정보를 가져옵니다…")
    jobs = fetch()
    if not jobs:
        print("받은 데이터가 없습니다. 파라미터/태그명을 확인하세요.")
        return
    payload = {"updated": dt.date.today().isoformat(), "jobs": jobs}
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"저장 완료: {OUTPUT}  ({len(jobs)}건)")


if __name__ == "__main__":
    main()
