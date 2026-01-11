# Feature Request

> **This document MUST result in a tracked issue.**  
> When completed, **always create or update a project issue** that links to this feature request and reflects its current state.

## Title
Add an adjuster to translate CV JSON into an arbitrary target language (LLM-backed)

## Description
Add a new adjuster that translates an extracted CV (structured JSON conforming to the cvextract schema) into an arbitrary target language, producing schema-valid translated JSON that can then be rendered with an existing DOCX template.

The feature should integrate into the existing composable CLI pipeline (Extract -> Adjust -> Render). The new adjuster will:
- Take `language=<target>` (e.g., `de`, `fr`, `es`, or "German", "French") as a required parameter.
- Translate only content fields, while preserving:
  - JSON schema structure and keys
  - formatting-relevant structural elements (lists, bullet arrays, etc.)
  - non-translatable identifiers (names, emails, URLs)
- Never Translate (this is crucial)
  - Technology names
  - Tool's Names
  - Programming Languages

The adjuster should be deterministic by default (temperature 0), and validate output against the CV schema before returning.

CLI example:
```
python -m cvextract.cli \
  --extract name=openai-extractor source=/path/to/cv.docx \
  --adjust name=openai-translate language=de \
  --render template=./examples/templates/CV_Template_Jinja2.docx \
  --target /tmp/out
```

## Motivation
- CVs often need to be submitted in a customer's/local language, not only tailored by role.
- Translating the structured representation keeps the workflow mechanical and repeatable (avoids editing Word docs manually).
- Benefits:
  - End users: quick translation without reformatting
  - Resourcing teams: translate many CVs consistently across languages/templates
  - Developers: translation becomes a reusable pipeline component (adjuster)

User stories:
- As a job seeker, I want to translate my CV to German while keeping the same template layout.
- As a staffing/resourcing team member, I want to batch translate multiple consultants' CV JSON to French and render them using a French DOCX template.
- As a developer, I want a pluggable adjuster so I can swap translation providers later.

## Must Have
- New adjuster: `openai-translate` appears in `--list adjusters`.
- Requires `language` parameter.
- Produces output that:
  - validates against the existing CV JSON schema
  - preserves schema structure and required fields
  - does not translate emails/URLs unless configured
- Deterministic defaults (e.g. temperature 0) and explicit model configuration.
- Clear error messages when translation fails or schema validation fails.
- No verification with the roundtrip verifier should happen
- Tests:
  - at least one "golden" fixture translating a small CV JSON to one target language
  - schema validation test for translated output
- Documentation updates:
  - README / CLI help shows how to translate and render with templates
  - specs updated to reflect new adjuster and parameters

## Should Have
- Language normalization:
  - accept ISO codes and names (e.g., `de`, `de-DE`, `German`)
  - This should be handled by the LLM, so it should be possible to give the language in any format.

## Should Not Have / Out of Scope
- Translating the DOCX file directly (translation happens on JSON, not on rendered documents).
- Automatic selection of language based on CV content.
- Fully offline translation (first implementation may require an API).
- Perfect localization of formatting conventions (dates/units) beyond basic translation.

## Alternatives Considered
- Translate after rendering DOCX:
  - rejected because it breaks determinism and makes layout/template fragile.
- External translation libraries (argos-translate, Marian, etc.):
  - rejected for v1 due to quality variance and added packaging complexity; could be a future provider.
- Manual translation in templates:
  - rejected because it pushes effort back to the user and doesn't scale.

## Risks & Trade-offs
- Hallucination / meaning drift in LLM translation:
  - mitigate with deterministic settings, glossary support, and schema validation.
- Proper nouns and company/product names may be incorrectly translated:
  - mitigate with "preserve proper nouns" default and glossary.
- Cost and rate limits for API-backed translation:
  - document clearly; allow users to choose model; enable batch/concurrency controls.
- Some fields may be ambiguous (short bullet points):
  - accept and rely on glossary and optional per-field translation controls.

## Success Criteria
- A user can run a single pipeline command that outputs a rendered DOCX in the target language using their chosen template.
- Translated JSON always validates against schema for standard fixtures.
- Minimal "surprise translations" (emails/URLs unchanged; proper nouns preserved by default).
- Add at least one real-world example in `examples/` that demonstrates translation + render.

## Additional Context / Mockups
- Example command:
  ```
  python -m cvextract.cli --extract source=/path/to/cv.docx --adjust name=openai-translate language=de --render template=/path/to/template.docx --target /output
  ```
- Expected pipeline artifact:
  - extracted.json (source language)
  - translated.json (target language)
  - rendered.docx (target language template)
  - no verification with the roundtrip verifier should happen

## Implementation Checklist (**Always Required**)
- [x] **Create or update a tracked issue for this feature**
- [x] Ensure the issue references this document and stays in sync
- [x] Add new tests if applicable
- [x] Extend existing tests if applicable
- [ ] Remove stale or unused tests and code
- [x] Identify and remove unused imports/usings/includes
- [ ] Run linters, analyzers, and formatters
- [x] **Update existing feature specification files under `specs/` to reflect this feature**
- [x] **Amend the relevant `specs/` files whenever requirements change during implementation**
- [x] Update README, help messages, and relevant documentation
- [ ] Ensure Codecov checks pass; if coverage drops, make a best effort to improve it
