from pathlib import Path
import yaml
import logging

from .settings import settings


sd: Path = Path(settings.skills_dir).resolve()
logger = logging.getLogger(__name__)


def construct_skill_text():
    the_text = ""
    skills_dict = {}
    for path in sd.rglob("*"):
        if path.is_file():
            skills_dict[path.parents[0].stem] = get_skill_header(path.resolve())
            print(f"Loaded skill description {path.parents[0].stem}")
            logger.debug(f"Loaded skill description {path.parents[0].stem}")

    for _, skill in skills_dict.items():
        the_text += (
            f"""\n<skill name="{skill["name"]}">\n{skill["description"]}\n<\\skill>\n"""
        )
    return the_text


def get_skill_header(filepath: Path) -> str:
    text = filepath.read_text().split("---")
    if len(text) >= 3:
        return yaml.safe_load(text[1])
    else:
        return ""


if __name__ == "__main__":
    print(construct_skill_text())
