"""
给 agent 一个查当前时间的能力（模型自己是不知道现在几点的）
"""
"""A tool that tells the agent the current time."""

import time
# 我们自己的工具也必须遵守 CoreCoder 的工具规范
from .base import Tool


class NowTool(Tool):
    name = "now"
    description = "Get the current local date and time. Use this when the user asks about the current time or you need a timestamp."
    parameters = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    def execute(self) -> str:
        return time.strftime("%Y-%m-%d %H:%M:%S")