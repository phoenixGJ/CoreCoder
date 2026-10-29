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

        # 确定 Skills（技能）文件夹的位置
        self.skills_dir = (
            skills_dir or Path.cwd() / "skills"
        ).resolve()

        #  创建一个空字典用于保存技能信息
        self.skills: dict[str, dict[str, str]] = {}

        # 自动扫描技能文件夹
        self.scan()

    # 主要负责解析mkdown文件的前置信息（frontmatter）和正文内容，并返回一个元组，包含解析出的元数据字典和正文字符串。
    # 主要做格式解析，不负责决定模型使用哪个技能。
    @staticmethod
    def parse_frontmatter(content: str) -> tuple[dict, str]:
        # 按行切分，并保留换行符，为了让后面能够正确恢复多行文本
        lines = content.splitlines(keepends=True)
        # 判断第一行是否为 ---
        if not lines or lines[0].strip() != "---":
            return {}, content
        # 从第二行开始查找，如果某一行是 ---，就提供这一行的索引
        end = next(
            (
                i for i, line in enumerate(lines[1:], start=1)
                if line.strip() == "---"
            ),
            None,
        )
        # 如果没有找到第二个 ---，就认为 Frontmatter 不完整
        if end is None:
            return {}, content
        # 元数据要完整才会进行提取
        try:
            # yaml.safe_load()：解析 YAML 元数据
            metadata = yaml.safe_load(
                "".join(lines[1:end])
            ) or {}
        except yaml.YAMLError:
            metadata = {}
        # 检查元数据是不是字典
        if not isinstance(metadata, dict):
            metadata = {}
        # body 在数据类型上是一整个字符串，在显示效果上依然可以是一行一行的，基本保留原文排版。
        body = "".join(lines[end + 1:]).strip()
        return metadata, body

    def scan(self) -> None:
        """为什么要清空？
        因为 scan() 可能被多次调用。例如你删除了某个 Skill，然后重新扫描，如果不清空，旧的技能可能仍然留在字典里。
        """
        self.skills.clear()
        # 判断指定路径是否存在，并且是否是文件夹。
        if not self.skills_dir.is_dir():
            return

        # 找到所有 SKILL.md 文件
        # glob() 是 Path 提供的方法，用于按照指定的路径模式寻找文件。
        # 找到的路径排序，保证每次按照稳定的顺序遍历。
        for manifest in sorted(self.skills_dir.glob("*/SKILL.md")):
            # 获取文件的真实路径(绝对路径)，为后面的安全检查做准备
            real_path = manifest.resolve()

            # 检查路径是否指向真实文件
            if not real_path.is_file():
                continue

            # 检查文件是否在 Skills 目录内部，意思就是只准读取skills目录下的SKILL.md文件
            if not real_path.is_relative_to(self.skills_dir):
                continue

            try:
                content = real_path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                continue

            metadata, body = self.parse_frontmatter(content)

            raw_name = metadata.get("name")
            name = raw_name.strip() if isinstance(raw_name, str) else ""
            # 如果 name 是非空字符串，就使用它；否则使用所在文件夹的名称
            # 即使 YAML 中没有写 name，程序仍然可以用文件夹名称作为技能名称
            name = name or manifest.parent.name

            raw_description = metadata.get("description")
            description = (
                raw_description.strip() if isinstance(raw_description, str) else ""
            )
            # 如果没有描述，就从正文提取
            # 如果 Frontmatter 没有提供描述，就取正文中第一行非空内容作为描述。
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
                # 保存的是完整的 SKILL.md 原始文本，包括 Frontmatter 和正文。
                "content": content,
            }
    # 把 self.skills 字典中保存的所有技能名称和描述，整理成一段方便阅读的字符串。
    def catalog(self) -> str:
        if not self.skills:
            return "(no skills found)"

        return "\n".join(
            f"- {skill['name']}: {skill['description']}"
            for skill in self.skills.values()
        )
    # 根据技能名称，从 self.skills 字典中找到对应的 Skill，并返回完整的 SKILL.md 内容
    def execute(self, name: str) -> str:
        skill = self.skills.get(name)

        if skill is not None:
            return skill["content"]

        available = ", ".join(self.skills) or "none"

        return f"Error: Unknown skill '{name}'. " f"Available: {available}"
