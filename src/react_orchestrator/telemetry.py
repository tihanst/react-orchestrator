import os
import uuid
from pathlib import Path
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider, ReadableSpan
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter


telem_log_file = Path(__file__).parent.parent.parent / "logs/telemetry/traces.json"
telem_jsonl_log_file = (
    Path(__file__).parent.parent.parent / "logs/telemetry/jsonl_traces.jsonl"
)


def setup_file_telemetry(
    telem_file_path: Path = telem_log_file,
    telem_jsonl_file_path: Path = telem_jsonl_log_file,
) -> str:
    telem_file_path.parent.mkdir(parents=True, exist_ok=True)
    telem_file_path.touch()
    telem_jsonl_file_path.parent.mkdir(parents=True, exist_ok=True)
    telem_jsonl_file_path.touch()

    # Keep LangChain OTel routing flags active
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_OTEL_ENABLED"] = "true"
    os.environ["LANGSMITH_OTEL_ONLY"] = "true"

    # One process run == one continuous conversation. Every span produced
    # during this run (across however many trace_ids get created for
    # follow-up questions) is tagged with this session.id resource attribute,
    # so traces can be grouped back into the conversation that produced them.
    # A new run generates a new session.id, starting a new superstructure.
    session_id = str(uuid.uuid4())
    resource = Resource.create({"session.id": session_id})

    provider = TracerProvider(resource=resource)

    # Open the target file in append mode
    telem_log_file_handle = open(telem_file_path, "a", encoding="utf-8")
    telem_jsonl_log_file_handle = open(telem_jsonl_file_path, "a", encoding="utf-8")

    def jsonl_formatter(span: ReadableSpan) -> str:
        return span.to_json(indent=None) + os.linesep

    # The ConsoleSpanExporter formats spans as regular JSON strings
    file_exporter = ConsoleSpanExporter(out=telem_log_file_handle)

    # The ConsoleSpanExporter formats spans as JSONL strings
    jsonl_file_exporter = ConsoleSpanExporter(
        out=telem_jsonl_log_file_handle, formatter=jsonl_formatter
    )

    # Batch the writes asynchronously to protect LangGraph's loop performance
    processor = BatchSpanProcessor(file_exporter)
    jsonl_processor = BatchSpanProcessor(jsonl_file_exporter)

    provider.add_span_processor(processor)
    provider.add_span_processor(jsonl_processor)

    trace.set_tracer_provider(provider)

    return session_id


# Just checking file paths
if __name__ == "__main__":
    print(os.listdir(Path(__file__).parent.parent.parent))
