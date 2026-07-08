import json
import logging
import os
import random
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from opentelemetry.trace import TraceFlags, SpanContext
from opentelemetry.sdk.trace import _Span
from opentelemetry.sdk.trace.export import SpanExportResult
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

# Surfaces the OTLP exporter's own error logging (status code + reason),
# which is otherwise silent since nothing else configures logging here.
logging.basicConfig(level=logging.INFO)

# Path matching your architecture
jsonl_log_file = Path(__file__).parent.parent / "logs/telemetry/jsonl_traces.jsonl"

# Tracks how far into the (append-only) jsonl log we've already uploaded,
# so re-running this script doesn't resend spans LangSmith already has.
offset_file = jsonl_log_file.parent / "jsonl_traces.uploaded_offset"

LANGSMITH_OTLP_ENDPOINT = "https://api.smith.langchain.com/otel/v1/traces"

load_dotenv(Path(__file__).parent.parent / ".env")


def _iso_to_ns(timestamp: str) -> int:
    return int(datetime.fromisoformat(timestamp.replace("Z", "+00:00")).timestamp() * 1e9)


def _new_trace_id() -> int:
    return random.getrandbits(128) or 1


def _new_span_id() -> int:
    return random.getrandbits(64) or 1


def _read_offset(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        return int(path.read_text().strip())
    except ValueError:
        return 0


class _StatusCapture(logging.Handler):
    """Grabs the HTTP status code the OTLP exporter logs on failure.
    exporter.export() only returns SUCCESS/FAILURE, not the status code,
    and LangSmith's endpoint upserts by span ID: a 409 means some spans in
    the batch already existed, not that the whole batch was rejected."""

    def __init__(self):
        super().__init__(level=logging.ERROR)
        self.status_code = None

    def emit(self, record):
        if record.args:
            self.status_code = record.args[0]


def _export(exporter: OTLPSpanExporter, spans: list) -> tuple[SpanExportResult, int | None]:
    capture = _StatusCapture()
    otlp_logger = logging.getLogger("opentelemetry.exporter.otlp.proto.http.trace_exporter")
    otlp_logger.addHandler(capture)
    try:
        result = exporter.export(spans)
    finally:
        otlp_logger.removeHandler(capture)
    return result, capture.status_code


def upload_offline_traces(file_path: Path, offset_path: Path):
    if not file_path.exists():
        print(f"Error: Log file not found at {file_path}")
        return

    start_offset = _read_offset(offset_path)

    api_key = os.environ.get("LANGSMITH_API_KEY")
    if not api_key:
        print("Error: LANGSMITH_API_KEY is not set. Add it to .env.")
        return

    headers = {"x-api-key": api_key}
    project = os.environ.get("LANGSMITH_PROJECT")
    if project:
        headers["Langsmith-Project"] = project

    # Target LangSmith's OTLP ingestion endpoint
    exporter = OTLPSpanExporter(endpoint=LANGSMITH_OTLP_ENDPOINT, headers=headers)

    print(f"Ingesting file: {file_path} (from byte offset {start_offset})")

    # LangSmith rejects re-sending a trace/span ID it has already seen -- even
    # after the run/project holding it is deleted, the ID itself stays "used".
    # So we mint fresh random IDs per upload and remap through these dicts,
    # keyed by the original hex id, to keep parent/child and trace grouping
    # intact without ever reusing an ID LangSmith might already know about.
    trace_id_map: dict[str, int] = {}
    span_id_map: dict[str, int] = {}

    spans = []
    end_offset = start_offset
    with open(file_path, "r", encoding="utf-8") as f:
        f.seek(start_offset)
        while True:
            line = f.readline()
            if not line:
                break
            end_offset = f.tell()
            if not line.strip():
                continue

            try:
                raw_span = json.loads(line.strip())
                
                # Extract OpenTelemetry identifiers and remap them to fresh,
                # never-before-seen IDs (see comment above trace_id_map).
                context_data = raw_span.get("context", {})
                orig_trace_id_hex = context_data.get("trace_id", "0x0")
                orig_span_id_hex = context_data.get("span_id", "0x0")
                trace_id = trace_id_map.setdefault(orig_trace_id_hex, _new_trace_id())
                span_id = span_id_map.setdefault(orig_span_id_hex, _new_span_id())

                # Check for parents to properly preserve your LangGraph or LLM chains tree.
                # The log stores this as "parent_id" (a bare span-id hex string, or null
                # for a root span) -- a span's parent is always in the same trace, so we
                # reuse this span's own (remapped) trace_id rather than looking for a
                # nested object.
                parent_id_hex = raw_span.get("parent_id")
                parent_span_context = None
                if parent_id_hex:
                    p_span_id = span_id_map.setdefault(parent_id_hex, _new_span_id())
                    parent_span_context = SpanContext(
                        trace_id=trace_id,
                        span_id=p_span_id,
                        is_remote=True,
                        trace_flags=TraceFlags(TraceFlags.SAMPLED)
                    )
                
                # Build context for the original span
                span_context = SpanContext(
                    trace_id=trace_id,
                    span_id=span_id,
                    is_remote=False,
                    trace_flags=TraceFlags(TraceFlags.SAMPLED)
                )
                
                # Map ISO-8601 timestamps back into nanosecond integers
                start_time_ns = raw_span.get("start_time")
                end_time_ns = raw_span.get("end_time")

                if isinstance(start_time_ns, str):
                    start_time_ns = _iso_to_ns(start_time_ns)
                if isinstance(end_time_ns, str):
                    end_time_ns = _iso_to_ns(end_time_ns)

                # Reconstruct the span object; start_time/end_time aren't
                # constructor args on _Span, they're set via start()/end()
                span = _Span(
                    name=raw_span.get("name", "replayed-span"),
                    context=span_context,
                    parent=parent_span_context,
                    resource=Resource.create(raw_span.get("resource", {}).get("attributes", {})),
                    attributes=raw_span.get("attributes", {}),
                )
                span.start(start_time=start_time_ns)
                span.end(end_time=end_time_ns)

                spans.append(span)

            except Exception as e:
                print(f"Skipping malformed trace line due to error: {e}")
                continue

    if not spans:
        print("No new spans to upload.")
        offset_path.write_text(str(end_offset))
        return

    print(f"Exporting {len(spans)} spans...")
    result, status_code = _export(exporter, spans)
    exporter.shutdown()

    if result == SpanExportResult.SUCCESS:
        offset_path.write_text(str(end_offset))
        print(f"Successfully sent {len(spans)} spans to LangSmith.")
    elif status_code == 409:
        # LangSmith already has some/all of these span IDs; the rest still
        # landed, so there's nothing left to retry.
        offset_path.write_text(str(end_offset))
        print(f"LangSmith already had some of these {len(spans)} spans (409); any new ones were still delivered.")
    else:
        print("Export FAILED. Offset not advanced, so a rerun will retry this same batch. See the error logged above for the status code and reason.")

if __name__ == "__main__":
    upload_offline_traces(jsonl_log_file, offset_file)
