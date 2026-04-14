"""
Minimal example: instrument any application with haic-libs.
Demonstrates the full pipeline in ~20 lines.
"""
from haic_logging import HaicLogger
from haic_metrics import report
import time

with HaicLogger(
    log_dir="./logs",
    pilot_tag="rag-demo",
    app_name="my_chatbot",
    app_version="0.1.0",
) as hl:

    # Simulate 3 turns
    for i in range(3):
        t0 = time.time()
        time.sleep(0.1)  # simulate user thinking

        hl.log_decision(
            actor_type="human",
            action="query",
            object_id=f"turn_{i}",
            duration_s=round(time.time() - t0, 3),
        )
        hl.log_decision(
            actor_type="ai",
            action="respond",
            object_id=f"turn_{i}",
            latency_ms=950,
            correct=True,
        )

    artifact_path = hl.export_decisions_artifact()

print(report(artifact_path))
