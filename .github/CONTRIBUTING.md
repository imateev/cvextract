# Contributing to cvextract

Thanks for your interest in contributing! 🎉

**cvextract** turns CVs into structured, validated JSON that can be automatically adapted and rendered into a new document (today: primarily DOCX). The core workflow is a composable CLI pipeline:

> **Extract → Adjust → Render**

The project is actively evolving. Contributions that improve correctness, determinism, and “real-world CV” robustness are especially welcome.

---

## Ways to contribute

You don’t need to write code to help:

- Fix docs, examples, CLI help text, or error messages
- Report bugs with minimal reproducible samples (ideally with sanitized CVs/templates)
- Add tests for edge-cases (formatting oddities, missing sections, etc.)
- Improve schema validation and clearer validation errors
- Implement or improve:
  - **Extractors** (new input formats or more robust parsing)
  - **Adjusters** (e.g., better tailoring logic, safer defaults)
  - **Renderers** (new output targets, better templating ergonomics)

---

## Getting started (dev setup)

### 1) Clone + install editable
```bash
git clone https://github.com/imateev/cvextract.git
cd cvextract
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows PowerShell

pip install -U pip
pip install -e .
