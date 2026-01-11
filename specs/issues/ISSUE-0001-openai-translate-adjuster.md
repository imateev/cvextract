# ISSUE-0001: OpenAI Translate Adjuster

## Status

- State: Implemented
- Owner: Unassigned
- Feature Request: `specs/feature-requests/openai-translate-adjuster.md`
- Specification: `specs/areas/adjustment/openai-translate-adjuster/README.md`

## Summary

Implement a translation adjuster that converts CV JSON into a target language while preserving schema structure, identifiers, and non-translatable terms. The adjuster integrates into the Extract -> Adjust -> Render pipeline and validates translated output before returning.

## Scope

- Add `openai-translate` adjuster and register in registry
- Translate content fields with deterministic defaults
- Preserve names, emails, URLs, tools, and programming languages
- Validate translated output against `cv_schema.json`
- Add tests and documentation

## Milestones

- [x] Implement adjuster and prompt
- [x] Register adjuster for `--list adjusters`
- [x] Add examples and documentation
- [x] Add translation tests and schema validation test

## Notes

- Keep this issue in sync with `specs/feature-requests/openai-translate-adjuster.md`.
