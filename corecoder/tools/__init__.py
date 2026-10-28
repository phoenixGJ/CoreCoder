"""Tool registry."""

from .agent import AgentTool
from .bash import BashTool
from .edit import EditFileTool
from .glob_tool import GlobTool
from .grep import GrepTool
from .read import ReadFileTool
from .todo import TodoWriteTool
from .write import WriteFileTool
from .now import NowTool
from .fetch_webpage import FetchWebpageTool
from .skill_loading import SkillLoadTool
ALL_TOOLS = [
    BashTool(),
    ReadFileTool(),
    WriteFileTool(),
    EditFileTool(),
    GlobTool(),
    GrepTool(),
    TodoWriteTool(),
    AgentTool(),
    # 注册 NowTool
    NowTool(),
    # 注册 FetchWebpageTool
    FetchWebpageTool(),
    # 注册 SkillLoadTool
    SkillLoadTool(),
]

