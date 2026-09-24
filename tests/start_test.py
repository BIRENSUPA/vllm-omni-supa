# Copyright (C) 2020-2026 Shanghai Biren Technology Co., Ltd.
"""CI 合跑入口 (testing_entrypoint).

Mirrors vllm-supa's ``test/start_test.py``: CI replaces ``-m pytest`` with this
script so all collected cases run under a single session and a shared summary.
Marker selection (``-m sanity`` / ``-m regression``) and paths are passed
through ``sys.argv`` by the CI harness, e.g.::

    python start_test.py -m sanity test/
"""

import sys

import pytest


class TestCollection:
    def __init__(self):
        self.config = ""
        self.collected = []

    def pytest_collection_modifyitems(self, config, items):
        self.config = config.option.markexpr
        for item in items:
            casename = [item.path]
            if casename not in self.collected:
                self.collected.append(casename)


class MyPlugin(TestCollection):
    def pytest_sessionfinish(self):
        print("\n Finish vllm-omni-supa pytest testing ")


if __name__ == "__main__":
    pytest_args = sys.argv[1:]
    ret = pytest.main(pytest_args, plugins=[MyPlugin()])
    print(f" Exit vllm-omni-supa pytest with code: {ret} ")
    sys.exit(ret)
