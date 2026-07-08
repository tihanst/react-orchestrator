import os
import uuid
from pathlib import Path
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider, ReadableSpan
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter



log_file = Path(__file__).parent.parent.parent / "logs/telemetry/traces.json"
jsonl_log_file = Path(__file__).parent.parent.parent / "logs/telemetry/jsonl_traces.jsonl"

log_file.parent.mkdir(parents=True, exist_ok=True)
log_file.touch()
jsonl_log_file.parent.mkdir(parents=True, exist_ok=True)
jsonl_log_file.touch()

def setup_file_telemetry(file_path: Path = log_file, jsonl_file_path: Path = jsonl_log_file) -> str:

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
    log_file = open(file_path, "a", encoding="utf-8")
    jsonl_log_file = open(jsonl_file_path, "a", encoding="utf-8")

    def jsonl_formatter(span: ReadableSpan) -> str:
        return span.to_json(indent=None) + os.linesep
    
    # The ConsoleSpanExporter formats spans as regular JSON strings
    file_exporter = ConsoleSpanExporter(out=log_file)
    
    # The ConsoleSpanExporter formats spans as JSONL strings
    jsonl_file_exporter = ConsoleSpanExporter(out=jsonl_log_file, formatter=jsonl_formatter)
    
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