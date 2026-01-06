import itertools
import json
import sys
from pathlib import Path

import pytest

from cvextract.cli_config import RenderStage, UserConfig
from cvextract.shared import UnitOfWork


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def make_render_work(tmp_path: Path):
    counter = itertools.count()

    def _make(
        cv_data: dict,
        template_path: Path,
        output_path: Path,
        input_path: Path | None = None,
        target_dir: Path | None = None,
    ) -> UnitOfWork:
        json_path = input_path or (tmp_path / f"input_{next(counter)}.json")
        json_path.write_text(json.dumps(cv_data, indent=2), encoding="utf-8")
        config = UserConfig(
            target_dir=target_dir or tmp_path,
            render=RenderStage(
                template=template_path,
                data=json_path,
                output=output_path,
            ),
        )
        return UnitOfWork(
            config=config,
            input=json_path,
            output=output_path,
            initial_input=json_path,
        )

    return _make
