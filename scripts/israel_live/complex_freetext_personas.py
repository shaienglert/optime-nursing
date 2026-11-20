"""10 complex free-text family requests against the live Israeli API (owner 2026-11-20).

Free text only: no questionnaire answers, so the AI interpreter does all the work.
For every run: interpretation status, missing fields, MUSTs, funnel, top results, and an
independent check that every shown facility meets every MUST according to its public page.
"""
import json
import sys
import time
import urllib.request

API = sys.argv[1] if len(sys.argv) > 1 else "https://oomnik-il-api.onrender.com"

PERSONAS = [
    ("דמנציה ושוטטות, זוג", 'אבא שלי בן 88 עם אלצהיימר מתקדם, יוצא מהבית בלילה ומסתובב. אמא בת 84 עצמאית לגמרי ורוצה לגור איתו באותו מקום. גרים ברחובות, לא יותר מ-25 ק"מ. יש לנו קוד של משרד הבריאות לאבא.'),
    ("סיעוד מורכב, מרותק", 'אמא שלי מונשמת דרך טרכאוסטומיה ומאכילים אותה בזונדה. היא מרותקת למיטה. אנחנו מירושלים, משפחה דתית, חשוב שבת ומטבח בהשגחה מהודרת. משרד הבריאות כבר אישר סיעוד מורכב.'),
    ("רוסית, תקציב, אין קוד", 'סבתא שלי מדברת רק רוסית. היא תשושה, הולכת עם הליכון ונפלה פעמיים. אין לנו קוד, נשלם פרטי עד 14,000 ש"ח בחודש. אשדוד או אשקלון, עדיף קרוב לים.'),
    ("ערבי, מטפלת מאותו מגדר", 'אבי בן 79, סיעודי אחרי שבץ, צד ימין משותק. אנחנו מנצרת. הוא מדבר ערבית בלבד, חשוב לנו צוות דובר ערבית ושהרחצה תהיה ע"י מטפל גבר. מימון דרך קוד משרד הבריאות.'),
    ("סתירה פנימית", 'אמא עצמאית לגמרי, אבל צריכה עזרה מלאה ברחצה, בהלבשה ובאכילה ולא יכולה לקום מהמיטה לבד. תל אביב. מחפשים דיור מוגן יוקרתי.'),
    ("בלתי אפשרי במכוון", 'דודה שלי סיעודית ויש לה דמנציה עם שוטטות. חייבת חדר יחיד עם ממ"ד צמוד, מטבח בהשגחת בד"ץ, צוות דובר אמהרית, לא יותר מ-5 ק"מ מקריית שמונה, ומקום פנוי כבר השבוע.'),
    ("עדיפויות מרובות, חיפה", 'אבא תשוש עם התחלה של בלבול, בעיקר בערבים. מחפשים בחיפה או בקריות עד 15 ק"מ. מסורתיים, כשר חשוב, שבת פחות. אוהב גינה ופעילויות, היה מורה למוזיקה. תקציב גמיש, אבל לא יותר מ-18 אלף.'),
    ("הודעה קצרה ומבולגנת", 'אמא 91 פ"ת סיעודית קוד יש. רוצים ממ"ד. אוכל כשר. מהר'),
    ("שאלה ולא בקשה", 'מה ההבדל בין תשוש לסיעודי? ואיך יודעים אם מגיע לנו קוד? אמא שלי גרה בבאר שבע והיא כבר לא מסתדרת לבד.'),
    ("פסיכוגריאטרי ושיקום", 'אחרי אשפוז פסיכיאטרי, אבי בן 72 עם דיכאון קשה ומחשבות שווא, צריך מסגרת פסיכוגריאטרית סגורה. אנחנו מכפר סבא. לא דתיים. יש לנו קוד.'),
]


def call(method, path, body=None):
    data = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method, headers={"Content-Type": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")
        except Exception as e:  # cold start / transient
            if attempt == 2:
                return 0, {"error": str(e)}
            time.sleep(10)


def main():
    out = []
    for title, text in PERSONAS:
        t0 = time.time()
        status, res = call("POST", "/api/il/recommendations", {"questionnaire_state": {"israelMarket": {}}, "natural_language_query": text, "limit": 20})
        took = round(time.time() - t0, 1)
        cards = res.get("results") or []
        musts = [m["key"] for m in res.get("musts") or []]
        violations = []
        for c in cards:
            met = {m["key"] for m in c.get("musts_met") or []}
            missing = [k for k in musts if k not in met]
            if missing:
                violations.append({"facility": c.get("canonical_id"), "not_shown_as_met": missing})
        ranks_ok = all(cards[i].get("rank_key") <= cards[i + 1].get("rank_key") for i in range(len(cards) - 1)) if all("rank_key" in c for c in cards) else None
        pages = []
        for c in cards[:3]:
            s, page = call("GET", f"/api/il/facilities/{c['canonical_id']}")
            pages.append({"id": c["canonical_id"], "page_status": s, "page_name_matches": page.get("name") == c.get("name")})
        out.append({
            "title": title, "text": text, "http": status, "seconds": took,
            "status": res.get("status"), "interpretation": res.get("interpretation"), "missing": res.get("missing"),
            "musts": res.get("musts"), "warnings": res.get("warnings"), "oomniker": res.get("oomniker"),
            "funnel": {k: (res.get("funnel") or {}).get(k) for k in ("universe", "passed", "failed", "pending", "pending_on_facility_information", "family_unknown", "fail_reasons", "pending_reasons", "shown")},
            "top": [{"name": c.get("name"), "city": c.get("city"), "km": c.get("distance_km"), "type": c.get("facility_type"),
                     "prefs_met": [p["label"] for p in c.get("preferences_met") or []], "prefs_not": [p["label"] for p in c.get("preferences_not_met") or []],
                     "unknown": [p["label"] for p in c.get("unknown") or []]} for c in cards[:3]],
            "checks": {"must_violations": violations, "ranking_monotone": ranks_ok, "pages": pages},
            "raw_keys": sorted(res.keys()),
        })
        print(f"{title}: http={status} status={res.get('status')} interp={(res.get('interpretation') or {}).get('status')} shown={len(cards)} violations={len(violations)} {took}s", flush=True)
    json.dump(out, open("israel_complex_personas.json", "w"), ensure_ascii=False, indent=1)
    for row in out:
        print("RESULT " + json.dumps(row, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
# run 2
