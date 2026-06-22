"""
fetch_jobs.py — 고용24 채용정보 → jobs.json
"""

import datetime as dt
import json
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path

API_KEY = os.environ.get("WORK24_API_KEY", "").strip()
OUTPUT = Path("jobs.json")

API_URL = "http://openapi.work.go.kr/opi/opi/opia/wantedApi.do"

QUERY_PARAMS = {
    "authKey": API_KEY,
    "callTp": "L",
    "returnType": "XML",
    "startPage": 1,
    "display": 100,
    "region": "11000",
    "pref": "12|B",
    "sortOrderBy": "DESC",
}


def _t(elem, tag):
    n = elem.find(tag)
    return n.text.strip() if (n is not None and n.text) else ""


def extract_gu(region):
    m = re.search(r"([가-힣]+구)", region or "")
    return m.group(1) if m else (region or "기타")


def fetch():
    import requests
    rows = []
    for page in range(1, 6):
        params = dict(QUERY_PARAMS, startPage=page)
        r = requests.get(API_URL, params=params, timeout=20)
        r.encoding = "utf-8"
        if page == 1:
            masked = r.url.replace(API_KEY, "***") if API_KEY else r.url
            print("HTTP 상태:", r.status_code)
            print("요청 URL:", masked)
            print("응답 미리보기:\n", r.text[:600], "\n---")
        try:
            root = ET.fromstring(r.text)
        except Exception as e:
            print("XML 파싱 실패:", e)
            break
        items = root.findall(".//wanted")
        if not items:
            break
        for it in items:
            region = _t(it, "region")
            holiday = _t(it, "holidayTpNm")
            title = _t(it, "title")
            rows.append({
                "title": title,
                "co":    _t(it, "company"),
                "gu":    extract_gu(region),
                "sal":   _t(it, "sal") or _t(it, "salTpNm") or "회사내규",
                "type":  "시간제" if ("시간" in (title + holiday)) else "전일제",
                "close": _t(it, "closeDt"),
                "url":   _t(it, "wantedInfoUrl") or "https://www.work24.go.kr",
            })
    seen, uniq = set(), []
    for x in rows:
        key = (x["co"], x["title"])
        if key not in seen:
            seen.add(key)
            uniq.append(x)
    return uniq


def main():
    jobs = []
    if not API_KEY:
        print("WORK24_API_KEY가 없습니다. 빈 목록으로 저장합니다.")
    else:
        print("고용24 API에서 채용정보를 가져옵니다…")
        try:
            jobs = fetch()
        except Exception as e:
            print("가져오기 중 오류:", e)
    payload = {"updated": dt.date.today().isoformat(), "jobs": jobs}
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"저장 완료: {OUTPUT}  ({len(jobs)}건)")


if __name__ == "__main__":
    main()
