from typing import Annotated, Any, Callable
from pathlib import Path
import os
from datetime import datetime
from functools import partial
import json

from tavily import TavilyClient
from pydantic import Field

from langchain_core.tools import tool # type: ignore

from .settings import settings

SETTINGS = settings

@tool 
def parallel_internet_research_agent(
    queries: Annotated[
        list[str],Field(description="Run multiple simultaneous standalone search queries for research to be done in parallel. "
        "Each item should be a full natural-language search statement or question, independent of the others. "
        )
    ]
    ) -> str:
    """Delegate one or more independent research sub-tasks to be searched and synthesized in parallel. 
    Use this instead of internet_research when the task can be split into multiple independent searches which will ultimately be synthesized.
    This tool is never executed directly, but is intercepted by the router to tringger the fan-out pattern via Send."""

    return ""


@tool
def internet_research(
        query: Annotated[
            str, 
            Field(description="The full, complete, and unmodified conversational question. "
            "CRITICAL: Do NOT extract keywords, summarize, or truncate. "
            "Pass the exact natural language intent."
            )
        ]
    ) -> str:
    """Executes a web search using the a websearch client.
    
    Use this tool to find up-to-date information on the web. 
    When calling this tool, you must pass the user's inquiry as a complete, 
    natural language sentence. Never convert the search intent into a concatenated 
    keyword string (e.g., do NOT pass 'best practices prompting LLM', 
    instead pass 'What are the best practices for prompting an LLM?')."""

    client = TavilyClient(api_key=SETTINGS.websearch_api_key)

    resp = client.search(
        query=query,
        search_depth='advanced',
        chunks_per_source=3,
        max_results=10,
        include_answer=True,
        include_raw_content=True,
        exclude_domains=['medium.com', 'linkedin.com', 'facebook.com'],
        include_usage=True   
    )

    with open(Path(SETTINGS.search_logs) / "search_logs.log", "a+") as f:
        try:
            
            final_payload: dict[str, Any] = {
                "single_or_multiple":"single",
                "time": datetime.now().strftime("%Y-%m-%d_%H:%M:%S"),
                "payload": resp 
            }
            
            f.write(json.dumps(final_payload) + '\n')
        
        except Exception as e:
            print(f"Problem json serializing with e as:\n{e}")

    results_list = [f"From {x["title"]}:\n{x["content"]}\n" for x in resp["results"]]
    
    return "\n".join(results_list)
    

@tool
def change_directory(
    directory: Annotated[
        str, Field(description="Path to the directory to change into; relative or absolute")
    ],
) -> str | None:
    """Change the current working directory to the given path."""
    path = Path(directory)

    try:
        os.chdir(path.resolve())
    except Exception:
        return f"Tried to change to directory {path.resolve()} but failed, check if it exists."


@tool
def list_directory(
    directory: Annotated[
        str | None, Field(description="Optional path. If not provided, lists the current directory.")
    ] = None,
) -> list[str] | str:
    """List the names of all entries in the given directory."""
    raw_path = directory if directory else "."
    path = Path(raw_path).expanduser().resolve()
    
    try:
        return [item.name for item in path.iterdir()]
    except Exception:
        return f"Tried to list directory {path} but failed, check if it exists."


@tool
def get_working_directory() -> str:
    """Return the absolute path of the current working directory."""
    return str(Path.cwd())


@tool
def path_exists(
    target: Annotated[str, Field(description="Path to check; relative or absolute")],
) -> bool:
    """Check whether a file or directory exists at the given path."""
    path = Path(target).expanduser().resolve()
    return path.exists()


@tool
def is_directory(
    target: Annotated[str, Field(description="Path to check; relative or absolute")],
) -> bool:
    """Check whether the given path exists and is a directory."""
    path = Path(target).expanduser()
    return path.is_dir()


@tool
def is_file(
    target: Annotated[str, Field(description="Path to check; relative or absolute")],
) -> bool:
    """Check whether the given path exists and is a regular file."""
    path = Path(target).expanduser()
    return path.is_file()


@tool
def get_absolute_path(
    target: Annotated[str, Field(description="Relative or absolute path to resolve")],
) -> str:
    """Return the fully resolved absolute path of the given path."""
    path = Path(target).expanduser()
    return str(path.resolve())


@tool
def list_files_recursive(
    directory: Annotated[
        str, Field(description="Directory to search under; defaults to the current working directory")
    ] = ".",
    pattern: Annotated[
        str, Field(description="Glob pattern to match filenames against, e.g. '*.py' or '*'")
    ] = "*",
) -> list[str] | str:
    """List all files matching the glob pattern recursively under the given directory."""
    path = Path(directory).expanduser().resolve()

    try:
        return [str(item) for item in path.rglob(pattern) if item.is_file()]
    except Exception:
        return f"Tried to search directory {path} but failed, check if it exists."


@tool
def make_directory(
    directory: Annotated[
        str,
        Field(description="Relative path of the directory to create; intermediate directories are created as needed if directory is nested."),
    ],
) -> str | None:
    """Create a directory along with any missing parent directories."""
    path = Path(".") / Path(directory).expanduser()
    if path.exists():
        return f"Directory {path.resolve()} already exists."
    try:    
        path.mkdir(parents=True)
    except Exception as e:
        return f"Tried to create directory tree {path.resolve()} but failed: {e}"


@tool
def get_file_size(
    target: Annotated[str, Field(description="Path to the file whose size should be returned")],
) -> int | str:
    """Return the size of the given file in bytes."""
    path = Path(target).expanduser().resolve()

    try:
        return path.stat().st_size
    except Exception:
        return f"Tried to get size of {path} but failed, check if it exists."


@tool
def find_file_in_directory(
    name: Annotated[str, Field(description="Filename to search for, e.g. 'config.json'")],
    directory: Annotated[
        str, Field(description="Directory to search in; defaults to the current working directory")
    ] = ".",
    fuzzy: Annotated[
        bool,
        Field(description="If True, fall back to case-insensitive substring matching when no exact match is found"),
    ] = True,
) -> list[dict[str, Any]] | str:
    """Non-recursive search for a file by name in a single directory.
    Looks only at the immediate contents — does not descend into subdirectories.
    Use find_file_in_current_and_subdirectories to search the whole tree.

    Returns a list of dicts with 'filename' and 'match_type' keys.
    Prefers exact name matches; falls back to case-insensitive substring matches if fuzzy is True and no exact match is found.
    """



    path = Path(directory).expanduser().resolve()

    # Catch propensity for LLMs to use * when asked if any files exist with particular type

    if '*' in name:

        recursive_call: Callable[[Any,Any, Any], Any] = partial(find_file_in_directory.func, directory=path, fuzzy=fuzzy) # IMPORTANT: find_file_in_directory is now a StructuredTool after being wrapped by @tool, so need to access .func attribute
        clean_name = [x for x in name.split('*') if x != '']
        matches = map(recursive_call, clean_name)
        
        final_match= []
        for x in matches: #a list of dictionaries {filename:xxx, matchtype:yyy}
            for dictionary in x:
                if dictionary['filename'] not in [val for x in final_match for val in x.values()]:
                    final_match.append(dictionary)
        return final_match


    try:
        all_files = [item for item in path.glob("*") if item.is_file()]
    except Exception:
        return f"Tried to search directory {path.resolve()} but failed, check if it exists."

    exact_matches = [
        {"filename": str(item), "match_type": "exact"}
        for item in all_files
        if item.name == name
    ]

    if exact_matches:
        return exact_matches

    if not fuzzy:
        return []

    name_lower = name.lower()
    fuzzy_matches = [
        {"filename": str(item), "match_type": "fuzzy"}
        for item in all_files
        if name_lower in item.name.lower()
    ]

    return fuzzy_matches


@tool
def find_file_in_directory_or_subdirectories(
    name: Annotated[str, Field(description="Filename to search for, e.g. 'config.json'")],
    directory: Annotated[
        str,
        Field(description="Directory to start the recursive search from; defaults to the current working directory"),
    ] = ".",
    fuzzy: Annotated[
        bool,
        Field(description="If True, fall back to case-insensitive substring matching when no exact match is found"),
    ] = True,
) -> list[dict[str, Any]] | str:
    """Recursive search for a file by name across an entire directory tree. Walks into all subdirectories.
    Use find_file_in_current_directory if you only want to search one level.

    Returns a list of dicts with 'filename' and 'match_type' keys.
    Prefers exact name matches; falls back to case-insensitive substring matches if fuzzy is True and no exact match is found.
    """
    path = Path(directory).expanduser().resolve()

    try:
        all_files = [item for item in path.rglob("*") if item.is_file()]
    except Exception:
        return f"Tried to search directory {path.resolve()} but failed, check if it exists."

    exact_matches = [
        {"filename": str(item), "match_type": "exact"}
        for item in all_files
        if item.name == name
    ]

    if exact_matches:
        return exact_matches

    if not fuzzy:
        return []

    name_lower = name.lower()
    fuzzy_matches = [
        {"filename": str(item), "match_type": "fuzzy"}
        for item in all_files
        if name_lower in item.name.lower()
    ]

    return fuzzy_matches


@tool
def search_file_contents(
    filepath: Annotated[str, Field(description="Path to the file to search within")],
    term: Annotated[
        str, Field(description="Keyword or phrase to search for; matching is case-insensitive")
    ],
    context: Annotated[
        int, Field(description="Number of context lines to include before and after each match")
    ] = 3,
) -> list[dict[str, Any]] | str:
    """Search a file for a keyword or phrase.

    Returns a list of dicts, each containing the matching line number, the
    matching line itself, and the surrounding context lines.
    """
    path = Path(filepath)

    try:
        lines = path.read_text(errors="replace").splitlines()
    except Exception:
        return f"Tried to read {path.resolve()} but failed, check if it exists and is a text file."

    term_lower = term.lower()
    matches: list[dict[str, Any]] = []

    for i, line in enumerate(lines):
        if term_lower not in line.lower():
            continue

        start = max(0, i - context)
        end = min(len(lines), i + context + 1)

        matches.append(
            {
                "filename": path.name,
                "full_file_path": path.resolve(),
                "line_number": i + 1,
                "match_line": line,
                "context": lines[start:end],
            }
        )

    return matches


@tool
def get_file_contents(
    file: Annotated[str, Field(description="file whose context to get; may include its filepath")],
    #token_limit: Annotated[Literal[1000], "Maximum number of tokens to return, do not override this"] = 1000,
) -> str:
    """Return the text contents of a file, truncated to approximately the value of token_limit (hard-coded in the function) tokens."""
    token_limit = 1000
    try:
        with open(Path(file).expanduser().resolve()) as f:
            content = f.read()
            if len(content) / 1.3 <= token_limit:
                return content
            else:
                return f"Returning approx. first {token_limit} tokens of text:\n{content[:token_limit]}"
    except (UnicodeDecodeError, FileNotFoundError, BaseException) as e:
        return f"File {file} was unreadable or binary."


@tool
def write_markdown_file(
    directory: Annotated[
        str, Field(description="Path to the directory to write the markdown file into; relative or absolute")
    ],
    info_to_write: Annotated[str, Field(description="Markdown formatted text to write to the file")],
    file_name: Annotated[str, Field(description="The name of the file to write to")],
) -> str | None:
    """Write markdown content to a timestamped file in the given directory, creating the directory if needed."""
    path = Path(directory).expanduser().resolve()
    
    path.mkdir(parents=True, exist_ok=True) 

    try:
        file_name_path = Path(file_name)
        full_write_path = path / Path(
            file_name_path.stem
            + datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
            + file_name_path.suffix
        )
        with open(full_write_path, "x") as f:
            f.write(info_to_write)
    except FileExistsError: # Should be impossible but just in case
        return f"File exists, won't overwrite to that path, try adding a random 2-digit number to {directory} and try again."


@tool
def get_full_directory_information(
    directory: Annotated[str, Field(description="Directory to get full information on")]
    ) -> list[dict[str,Any]]:
    """Get information and statistics about contents of given directory."""
    
    direct = Path(directory).expanduser().resolve()
    results: list[dict[str, Any]] = []
    with os.scandir(direct) as entries:
        for entry in entries:
            stat = entry.stat()
            temp: dict[str,Any] = {
                "name": entry.name,
                "is_file": entry.is_file(),
                "last_modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d_%H:%M:%S"),
                "size": f"{stat.st_size / 1024**2} MB"
            }
            results.append(temp)
    return results


# Tool registry

TOOL_NODE_ROUTED_TOOLS = [
    internet_research,
    change_directory,
    list_directory,
    get_working_directory,
    path_exists,
    list_files_recursive,
    make_directory,
    get_file_size,
    find_file_in_directory,
    find_file_in_directory_or_subdirectories,
    search_file_contents,
    get_file_contents,
    write_markdown_file,
    get_full_directory_information
] # Everything except parallel_internet_research_agent

VIRTUAL_TOOLS_FAN_OUT = [
    parallel_internet_research_agent
]

ALL_TOOLS = TOOL_NODE_ROUTED_TOOLS + VIRTUAL_TOOLS_FAN_OUT
