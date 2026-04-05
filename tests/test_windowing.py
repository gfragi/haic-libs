from datetime import datetime, timezone

from haic_metrics.windowing import filter_decisions_events_by_epoch

def test_absolute_iso_window():
    # create times that definitely fall inside the window
    start = datetime(2023, 11, 14, 0, 0, 0, tzinfo=timezone.utc).timestamp()
    end   = datetime(2023, 11, 14, 0, 10, 0, tzinfo=timezone.utc).timestamp()

    decisions = [
        {"t": start + 1},
        {"t": start + 600},   # exactly end boundary
        {"t": start + 1200},  # outside
    ]

    window = {
        "basis": "absolute",
        "start": "2023-11-14T00:00:00Z",
        "end": "2023-11-14T00:10:00Z",
    }

    d_f, _, summary = filter_decisions_events_by_epoch(
        artifact=None,
        decisions=decisions,
        window=window,
    )

    assert len(d_f) == 2
    assert summary["duration_s"] == 600.0
