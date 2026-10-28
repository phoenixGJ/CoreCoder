"""Base class for all tools."""

import threading
from abc import ABC, abstractmethod

# File-mutating tools (write_file/edit_file) serialize on this, so a parallel
# batch can't interleave read-modify-write on the same file and lose an edit.
FILE_MUTATION_LOCK = threading.Lock()

# ABC 是 Python 中的抽象基类（Abstract Base Class）
# 理解为：Tool 是所有具体工具都要遵守的一套规则。
class Tool(ABC):
    """Minimal tool interface. Subclass this to add new capabilities."""

    name: str
    description: str
    """采用的是 JSON Schema，简单理解就是：用一种标准格式告诉大模型：这个工具需要哪些参数、参数是什么类型、哪些是必填的。"""
    parameters: dict  # JSON Schema for the function args

    @abstractmethod
    # @abstractmethod 表示这是一个抽象方法
    # 意思是：所有能够实例化的具体工具类，都必须实现这个方法，不能只继承一个空方法就直接使用。
    def execute(self, **kwargs) -> str:
        """Run the tool and return a text result."""
        ...
    # schema() 的任务是把工具的信息整理成大模型 API 能理解的格式。 
    """
    Agent 把这个 Schema 随模型请求一起发送。
    模型就知道：我可以调用 read_file 工具，而且调用时需要传入 file_path。
    schema() 并不会真正执行工具，它只是向大模型介绍工具。 JSON Schema 也不会因为写在这里就自动完成运行时参数校验。
    """
    def schema(self) -> dict:
        """OpenAI function-calling schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
