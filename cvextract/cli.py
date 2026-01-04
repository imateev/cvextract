#!/usr/bin/env python3
# Copyright 2025 Ivo Mateev
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Command-line interface for cvextract.

Three-phase architecture:
1. Gather user requirements (parse args) -> UserConfig
2. Prepare execution environment (validate, create dirs)
3. Execute pipeline (run operations with explicit paths)
"""

from __future__ import annotations

import traceback
from pathlib import Path
from typing import List, Optional

from cvextract.cli_gather import gather_user_requirements
from cvextract.cli_prepare import prepare_execution_environment
from cvextract.cli_execute import execute_pipeline
from cvextract.logging_utils import LOG, setup_logging


def main(argv: Optional[List[str]] = None) -> int:
    """
    Main CLI entry point with three-phase architecture.
    
    Phase 1: Gather user requirements (parse args)
    Phase 2: Prepare execution environment (validate, setup)
    Phase 3: Execute pipeline (run operations)
    """
    # Phase 1: Gather requirements
    config = gather_user_requirements(argv)
    
    # Setup logging (side effect necessary for all phases)
    if config.log_file:
        Path(config.log_file).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
    setup_logging(config.debug, log_file=config.log_file, verbosity=config.verbosity)
    
    try:
        # Phase 2: Prepare environment
        config = prepare_execution_environment(config)
        
        # Phase 3: Execute
        return execute_pipeline(config)
    except Exception as e:
        LOG.error(str(e))
        if config.debug or config.verbosity >= 2:
            LOG.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    raise SystemExit(main())


