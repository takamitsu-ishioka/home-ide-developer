#!/usr/bin/env python3
import sys
import json
from datetime import date


def iter_records(data):
    if isinstance(data, list):
        sources = data
    elif isinstance(data, dict):
        sources = data.get("work_records", [])
    else:
        sources = []

    for item in sources:
        if not isinstance(item, dict):
            continue
        if isinstance(item.get("work_record"), dict):
            yield item["work_record"]
        elif isinstance(item.get("work_records"), list):
            for record in item["work_records"]:
                if isinstance(record, dict):
                    yield record
        else:
            yield item


def main():
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"calc_avg_work_time.py: Failed to parse JSON: {e}", file=sys.stderr)
        sys.exit(1)

    records = list(iter_records(data))
    if not records:
        print("calc_avg_work_time.py: No work records in input", file=sys.stderr)
        sys.exit(1)

    today = date.today()
    worked = []

    for r in records:
        if "date" not in r:
            continue
        record_date = date.fromisoformat(r["date"])
        if record_date > today:
            continue
        # freee HR API: total_work_mins = clock-out minus clock-in minus breaks
        mins = int(r.get("total_work_mins") or 0)
        if mins > 0:
            worked.append({"date": r["date"], "mins": mins})

    if not worked:
        print("calc_avg_work_time.py: No worked days found this month so far", file=sys.stderr)
        sys.exit(1)

    total_mins = sum(d["mins"] for d in worked)
    num_days = len(worked)
    avg_mins = total_mins / num_days

    def fmt(mins):
        return f"{int(mins // 60)}h {int(mins % 60):02d}m"

    print(f"Period        : {worked[0]['date']} - {worked[-1]['date']}")
    print(f"Worked days   : {num_days}")
    print(f"Total work    : {fmt(total_mins)}")
    print(f"Average / day : {fmt(avg_mins)}")


if __name__ == "__main__":
    main()
