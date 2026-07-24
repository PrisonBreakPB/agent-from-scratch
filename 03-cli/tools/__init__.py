from .bash import bash
from .read_file import read_file
from .write_file import write_file
from .edit_file import edit_file
from .glob import glob
from .grep import grep

# 工具 Schema
tools = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "执行 bash 命令，用于运行程序、系统操作等。适合执行 shell 命令、git 操作、运行脚本等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "要执行的 bash 命令"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "超时时间（秒），默认 120"
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取文件内容。在编辑文件前，应该先用这个工具读取文件内容。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "文件路径"
                    },
                    "offset": {
                        "type": "integer",
                        "description": "起始行号（从1开始），默认1"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "最多读取行数，默认2000"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "创建新文件或完全重写已有文件。适合创建新文件、写入完整内容。如果只是修改已有文件的一小部分，请用 edit_file。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "文件路径"
                    },
                    "content": {
                        "type": "string",
                        "description": "要写入的内容"
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "编辑已有文件，替换指定的文本内容。适合修改文件的一小部分（如改一行代码、加一个函数）。如果是创建新文件或完全重写，请用 write_file。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "文件路径"
                    },
                    "old_text": {
                        "type": "string",
                        "description": "要替换的原文本"
                    },
                    "new_text": {
                        "type": "string",
                        "description": "替换后的新文本"
                    }
                },
                "required": ["path", "old_text", "new_text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "glob",
            "description": "查找匹配模式的文件，支持通配符。适合查找特定类型的文件（如所有 .py 文件）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "文件匹配模式，如 '*.py' 或 '**/*.txt'"
                    },
                    "path": {
                        "type": "string",
                        "description": "搜索目录，默认当前目录"
                    }
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "grep",
            "description": "在文件中搜索内容。适合查找特定代码、函数名、变量名等。返回匹配的文件路径和行号。",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "搜索的文本或正则表达式"
                    },
                    "path": {
                        "type": "string",
                        "description": "搜索路径，默认为当前目录"
                    },
                    "include": {
                        "type": "string",
                        "description": "只搜索匹配的文件，如 '*.py'"
                    }
                },
                "required": ["pattern"]
            }
        }
    }
]

# 函数映射
available_functions = {
    "bash": bash,
    "read_file": read_file,
    "write_file": write_file,
    "edit_file": edit_file,
    "glob": glob,
    "grep": grep
}
