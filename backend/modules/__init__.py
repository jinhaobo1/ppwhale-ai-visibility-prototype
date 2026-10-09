"""模块注册表：框架通过这里发现所有维度模块。

新增模块步骤：
1. 在 modules/ 下建一个文件夹（如 modules/xxx/）
2. 写 run(context) -> list[dict] 入口函数
3. 在这里 import 并加入 MODULES 列表

框架 engine.py 会自动遍历 MODULES，把每个模块产出的检查项汇总起来。
"""
from modules import find, see, understand, trust, cite

MODULES = [find, see, understand, trust, cite]
