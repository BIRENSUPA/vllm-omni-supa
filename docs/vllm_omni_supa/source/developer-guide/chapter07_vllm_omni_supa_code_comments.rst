代码注释规范
============

代码注释分为 CPP/SUDA 层和 Python 层。注释应解释实现原因、接口约束和容易被误改的
行为；不要为显而易见的赋值或控制流添加逐行旁白。

CPP/SUDA 层注释
---------------

在 ``.cpp``、``.cu`` 和 ``.su`` 文件中，复杂 kernel 或 binding 前应说明：

* 输入输出的形状、数据类型、布局和量化粒度。
* grid/block 映射、同步要求以及 BR2XX/SUDA 特有的限制。
* 性能相关选择（例如 tile 大小、临时 workspace）及其适用条件。
* 与 Python custom op schema 的对应关系，以及异常输入的处理方式。

使用 ``//`` 编写简短行注释，使用 ``/* ... */`` 说明跨行约束；内核实现的关键步骤
应在逻辑块前集中说明：

.. code-block:: cpp

   // One output row maps to one BR2XX program instance. Keep the layout
   // contiguous because the SUDA kernel assumes unit-stride access.
   void launch_layernorm(const Tensor& input, Tensor& output) {
       // The reduction must complete before the normalization write-back.
       reduce_row(input, output);
   }

Python 层注释和文档字符串（PEP 257）
--------------------------------------

在 ``vllm_omni_supa/`` Python 模块中，模块、类、公共函数和方法使用 docstring
说明用途和行为；实现附近的注释解释原因、约束和容易被误改的逻辑。docstring 遵循
`PEP 257 <https://peps.python.org/pep-0257/>`_：

* docstring 必须是模块、类或函数体中的第一条语句。
* 简短对象使用以句号结尾的单行摘要；多行 docstring 首行摘要，空一行后说明参数、返回值、异常和副作用。
* 使用三重双引号（``"""``）。补丁函数说明被替换的 upstream 接口和兼容性要求。
* 注释说明 upstream 行为、环境变量、dispatch key、设备检查、fallback、monkey patch 导入顺序和幂等性。
* Fake/Meta 算子仅用于 ``torch.compile`` 的形状和设备传播，不提供真实数值结果。

.. code-block:: python

   def register_patch() -> None:
       """Apply vLLM-Omni-SUPA runtime patches once.

       Repeated plugin discovery is safe and does not register operators twice.
       """
       apply_patches()

不要用行尾注释替代接口文档；当实现逻辑变化时，应同步更新 docstring 和相关注释。
