"""
Compare one overnight_diary.py run with the answer key of the synthetic day.
The pipeline never reads ground_truth.json; only this script does.

    python evaluate.py runs/2026-10-27 sample_day/ground_truth.json
"""
import itertools
import json
import pathlib
import sys

run, truth = pathlib.Path(sys.argv[1]), json.loads(pathlib.Path(sys.argv[2]).read_text())
frames = {f["frame"]: f for f in json.loads((run / "frames.json").read_text())}
events = json.loads((run / "events.json").read_text())
chapters = json.loads((run / "draft.json").read_text())["chapters"]

expect = {i["file"]: i for i in truth["images"]}
should_drop = {f for f, i in expect.items() if i["event_id"] == "quality_filter" or "deduplicate" in i["test_purpose"]}
dropped = {f for f, x in frames.items() if x["drop"]}

print("1. filtering")
for f in sorted(expect):
    x = frames[f]
    ok = (f in dropped) == (f in should_drop)
    print(f"  {'ok ' if ok else 'MISS'} {f}  brightness {x['brightness']:>5}  sharpness {x['sharpness']:>7}  "
          f"{x['drop'] or 'kept'}")

# grouping: for every pair of kept frames, same event in the run iff same event in the key
event_of = {n: e["id"] for e in events for n in e["frames"]}
kept = sorted(event_of)
pairs = list(itertools.combinations(kept, 2))
agree = sum((event_of[a] == event_of[b]) == (expect[a]["event_id"] == expect[b]["event_id"]) for a, b in pairs)
print(f"\n2. grouping: {len(events)} events, key has "
      f"{len({i['event_id'] for f, i in expect.items() if f not in should_drop})}; "
      f"pairwise agreement {agree}/{len(pairs)}")
for e in events:
    print(f"  {e['id']} {e['start'][11:16]}-{e['end'][11:16]}  " +
          ", ".join(f"{n} ({expect[n]['event_id']})" for n in e["frames"]))

print(f"\n3. draft: {len(chapters)} chapters, {sum(1 for c in chapters if c['flags'])} flagged")
for c in chapters:
    print(f"  [{c['time']}] {c['title']}: {c['text']}" + (f"  FLAGS {c['flags']}" if c["flags"] else ""))
print("\nThe claims in each chapter still need a human read against the photos; this script only checks structure.")
