# Feature Request: Unified and Immutable Prompt Handling for All Components Interacting with OpenAI

## Description
Currently, in `openai_extractor.py`, prompts sent to OpenAI are stored as inline strings in the Python file.  In other parts of the project, prompts are stored under `ml_adjustments/prompts`. This inconsistency makes the codebase harder to understand, extend, and package. 

All components that interact with OpenAI must handle prompts in **one unified, well-defined way**.  Prompts must be **immutable**, shipped with the package, and loaded in a platform-independent manner so the package works reliably on Windows, macOS, and Linux after installation. 

The solution should be robust, easy to use for contributors, and safe against missing files or path-related issues. 

## Motivation
- Consistency: contributors should have a single, documented way to add or modify prompts.
- Maintainability: one approach reduces confusion and onboarding friction.
- Reliability: packaging and installation should never fail due to missing or mislocated prompt files.
- Cross-platform support: behavior must be identical across operating systems.

## Must Have
- All prompts used by OpenAI-interacting components are handled **identically**.
- No inline prompt bodies remain in Python source files (only references/keys if needed).
- Prompts are **immutable** at runtime (users cannot modify them via local files).
- Prompts are shipped as part of the installed package and loaded in a platform-independent way.
- After packaging and installing the project on a different machine, the application runs successfully on example CSVs without failing due to missing prompt files.
- A single shared mechanism/module is responsible for loading prompts.

## Should Have
- Clear documentation explaining how to add a new prompt.
- A small smoke test or check proving prompt loading works from an installed package artifact.

## Should Not Have / Out of Scope
- Any changes to business logic or OpenAI interaction logic unrelated to prompt handling. 
- Any form of runtime prompt editing or user-provided prompt overrides.
- Refactors beyond what is strictly required for consistent prompt handling.

## Alternatives Considered
- Keeping prompts as inline strings in Python files (rejected due to inconsistency and poor scalability).
- Loading prompts via relative filesystem paths (rejected due to cross-platform and packaging fragility).

## Risks &amp; Trade-offs
- Incorrect packaging configuration could lead to prompts not being included in the distribution.
- Making prompts immutable reduces flexibility, but significantly improves reliability and reproducibility. 

## Success Criteria
- All features use the same prompt-loading mechanism.
- The package can be installed on different platforms and used successfully without manual setup.
- No runtime errors related to missing or inaccessible prompt files.
- Contributors can clearly see where prompts live and how they are loaded. 

## Additional Context / Mockups
- Prompts are expected to live under a dedicated prompts directory within the package (e.g.  `ml_adjustments/prompts`).
- Prompt access should not rely on relative paths from the working directory.

## Implementation Checklist (**Always Required**)
- [x] Add new tests if applicable
- [x] Extend existing tests if applicable
- [ ] Remove stale or unused tests and code
- [ ] **Identify and remove unused imports/usings/includes**
- [ ] Run linters, analyzers, and formatters to catch unused usings automatically
- [x] Ensure prompts are included in the packaged artifact and loadable after installation
- [ ] Extend or update existing specs and documentation as needed
- [ ] Extend or update README, help messages, and relevant documentation
- [x] **Add this feature request verbatim to the feature spec as `ORIGINAL_FEATURE_REQUEST.md`**
- [ ] Ensure Codecov checks pass; if coverage drops, make a best effort to improve it
