"""Load skill instructions from SKILL.md files."""

from pathlib import Path
from typing import ClassVar

import yaml

from .base import Tool


class SkillLoadTool(Tool):
    name = "load_skill"

    description = (
        "Load the full instructions of a skill by its name. "
        "Use this tool when a skill is relevant to the user's task."
    )

    parameters: ClassVar[dict] = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "The name of the skill to load",
            }
        },
        "required": ["name"],
    }

    # 表示可以传入技能文件夹路径，也可以不传。
    def __init__(self, skills_dir: Path | None = None):
        # 选择目录，再转换成绝对路径：
        self.skills_dir = (
            skills_dir or Path.cwd() / "skills"
        ).resolve()

        self.skills: dict[str, dict[str, str]] = {}

        self.scan()

    # 主要负责解析mkdown文件的前置信息（frontmatter）和正文内容，并返回一个元组，包含解析出的元数据字典和正文字符串。
    # 主要做格式解析，不负责决定模型使用哪个技能。    
    @staticmethod
    def parse_frontmatter(content: str) -> tuple[dict, str]:
        lines = content.splitlines(keepends=True)

        if not lines or lines[0].strip() != "---":
            return {}, content

        end = next(
            (
                i for i, line in enumerate(lines[1:], start=1)
                if line.strip() == "---"
            ),
            None,
        )

        if end is None:
            return {}, content

        try:
            metadata = yaml.safe_load(
                "".join(lines[1:end])
            ) or {}
        except yaml.YAMLError:
            metadata = {}

        if not isinstance(metadata, dict):
            metadata = {}

        body = "".join(lines[end + 1:]).strip()
        return metadata, body

    def scan(self) -> None:
        self.skills.clear()

        if not self.skills_dir.is_dir():
            return

        for manifest in sorted(self.skills_dir.glob("*/SKILL.md")):
            real_path = manifest.resolve()

            if not real_path.is_file():
                continue

            if not real_path.is_relative_to(self.skills_dir):
                continue

            try:
                content = real_path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                continue

            metadata, body = self.parse_frontmatter(content)

            raw_name = metadata.get("name")
            name = raw_name.strip() if isinstance(raw_name, str) else ""
            name = name or manifest.parent.name

            raw_description = metadata.get("description")
            description = (
                raw_description.strip() if isinstance(raw_description, str) else ""
            )

            if not description:
                description = next(
                    (
                        line.lstrip("# ").strip()
                        for line in body.splitlines()
                        if line.strip()
                    ),
                    f"Skill: {name}",
                )

            description = " ".join(description.split())

            self.skills[name] = {
                "name": name,
                "description": description,
                "content": content,
            }

    def catalog(self) -> str:
        if not self.skills:
            return "(no skills found)"

        return "\n".join(
            f"- {skill['name']}: {skill['description']}"
            for skill in self.skills.values()
        )

    def execute(self, name: str) -> str:
        skill = self.skills.get(name)

        if skill is not None:
            return skill["content"]

        available = ", ".join(self.skills) or "none"

        return f"Error: Unknown skill '{name}'. " f"Available: {available}"
