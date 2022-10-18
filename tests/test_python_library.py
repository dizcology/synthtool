# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import shutil
from pathlib import Path

from packaging import version as packaging_version
import pytest

from synthtool import gcp
from synthtool.sources import templates
from synthtool.languages import python
from . import util


PYTHON_LIBRARY = Path(__file__).parent.parent / "synthtool/gcp/templates/python_library"


@pytest.mark.parametrize(
    ["template_kwargs", "expected_text"],
    [
        ({}, ["import nox", 'session.install("-e", ".", *constraints)']),
        (
            {"unit_test_local_dependencies": ["../testutils", "../unitutils"]},
            [
                """\
UNIT_TEST_LOCAL_DEPENDENCIES = [
    "../testutils",
    "../unitutils",
]""",
            ],
        ),
        (
            {"system_test_local_dependencies": ["../testutils", "../sysutils"]},
            [
                """\
SYSTEM_TEST_LOCAL_DEPENDENCIES = [
    "../testutils",
    "../sysutils",
]""",
            ],
        ),
        (
            {"unit_test_extras": ["abc", "def"]},
            [
                """\
UNIT_TEST_EXTRAS = [
    "abc",
    "def",
]""",
            ],
        ),
        (
            {"system_test_extras": ["abc", "def"]},
            """\
SYSTEM_TEST_EXTRAS = [
    "abc",
    "def",
]""",
        ),
        (
            {"unit_test_extras_by_python": {"3.8": ["abc", "def"]}},
            [
                """\
UNIT_TEST_EXTRAS_BY_PYTHON = {
    "3.8": [
        "abc",
        "def",
    ],
}""",
            ],
        ),
        (
            {"system_test_extras_by_python": {"3.8": ["abc", "def"]}},
            [
                """\
SYSTEM_TEST_EXTRAS_BY_PYTHON = {
    "3.8": [
        "abc",
        "def",
    ],
}""",
            ],
        ),
        (
            {
                "unit_test_extras": ["tuv", "wxyz"],
                "unit_test_extras_by_python": {"3.8": ["abc", "def"]},
            },
            [
                """\
UNIT_TEST_EXTRAS = [
    "tuv",
    "wxyz",
]""",
                """\
UNIT_TEST_EXTRAS_BY_PYTHON = {
    "3.8": [
        "abc",
        "def",
    ],
}""",
            ],
        ),
        (
            {
                "system_test_extras": ["tuv", "wxyz"],
                "system_test_extras_by_python": {"3.8": ["abc", "def"]},
            },
            [
                """\
SYSTEM_TEST_EXTRAS = [
    "tuv",
    "wxyz",
]""",
                """\
SYSTEM_TEST_EXTRAS_BY_PYTHON = {
    "3.8": [
        "abc",
        "def",
    ],
}""",
            ],
        ),
    ],
)
def test_library_noxfile(template_kwargs, expected_text):
    t = templates.Templates(PYTHON_LIBRARY)
    result = t.render(
        "noxfile.py.j2",
        **template_kwargs,
    ).read_text()
    # Validate Python syntax.
    result_code = compile(result, "noxfile.py", "exec")
    assert result_code is not None
    for expected in expected_text:
        assert expected in result


def test_python_library():
    with util.chdir(Path(__file__).parent / "fixtures/python_library"):
        template_dir = Path(__file__).parent.parent / "synthtool/gcp/templates"
        common = gcp.CommonTemplates(template_path=template_dir)
        templated_files = common.py_library()

        assert os.path.exists(templated_files / ".kokoro/docs/docs-presubmit.cfg")
        assert os.path.exists(templated_files / ".kokoro/docker/docs/Dockerfile")


def test_split_system_tests():
    with util.chdir(Path(__file__).parent / "fixtures/python_library"):
        template_dir = Path(__file__).parent.parent / "synthtool/gcp/templates"
        common = gcp.CommonTemplates(template_path=template_dir)
        templated_files = common.py_library(split_system_tests=True)

        with open(templated_files / ".kokoro/presubmit/presubmit.cfg", "r") as f:
            contents = f.read()
            assert "RUN_SYSTEM_TESTS" in contents
            assert "false" in contents

        assert os.path.exists(templated_files / ".kokoro/presubmit/system-3.8.cfg")
        with open(templated_files / ".kokoro/presubmit/system-3.8.cfg", "r") as f:
            contents = f.read()
            assert "system-3.8" in contents


@pytest.mark.parametrize(
    "fixtures_dir",
    [
        Path(__file__).parent / "fixtures/python_library",  # just setup.py
        Path(__file__).parent
        / "fixtures/python_library_w_version_py",  # has google/cloud/texttospeech/version.py
    ],
)
def test_get_library_version(fixtures_dir):
    with util.copied_fixtures_dir(fixtures_dir):
        t = templates.Templates(PYTHON_LIBRARY)
        result = t.render(".github/release-please.yml")
        os.makedirs(".github")
        shutil.copy(result, Path(".github/release-please.yml"))

        version = python.get_library_version()
        assert version == packaging_version.Version('2.11.0')


@pytest.mark.parametrize(
    "fixtures_dir",
    [
        Path(__file__).parent / "fixtures/python_library",  # just setup.py
        Path(__file__).parent
        / "fixtures/python_library_w_version_py",  # has google/cloud/texttospeech/version.py
    ],
)
def test_configure_previous_major_version_branches(fixtures_dir):
    with util.copied_fixtures_dir(fixtures_dir):
        t = templates.Templates(PYTHON_LIBRARY)
        result = t.render(".github/release-please.yml")
        os.makedirs(".github")
        shutil.copy(result, Path(".github/release-please.yml"))

        python.configure_previous_major_version_branches()
        release_please_yml = Path(".github/release-please.yml").read_text()

        assert (
            release_please_yml
            == """releaseType: python
handleGHRelease: true
# NOTE: this section is generated by synthtool.languages.python
# See https://github.com/googleapis/synthtool/blob/master/synthtool/languages/python.py
branches:
- branch: v1
  handleGHRelease: true
  releaseType: python
- branch: v0
  handleGHRelease: true
  releaseType: python
"""
        )
