"""全局业务枚举。

题目模块、题型在 seed、服务层、接口层和前端之间传递，之前都是散落的字符串。
统一到这里后，任何一处拼错都会在入口处直接报错，而不是静默返回空列表。
"""

from enum import Enum


class Module(str, Enum):
    NETWORK = "network"
    OS = "os"
    MYSQL = "mysql"
    REDIS = "redis"


class QuestionType(str, Enum):
    CHOICE = "choice"
    SHORT_ANSWER = "short_answer"


MODULES = tuple(module.value for module in Module)
QUESTION_TYPES = tuple(question_type.value for question_type in QuestionType)
