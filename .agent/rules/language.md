---
trigger: always_on
---

# Language & Communication Protocol

## 1. Output Language
You must strictly use **Simplified Chinese (简体中文)** for all interactions, including:
* **Chat Responses:** All replies to the user.
* **Walkthroughs & Planning:** The step-by-step reasoning and plans must be written in Chinese.
* **Implementation Explanations:** When explaining code or writing commit messages.
* **Documentation:** The `README.md` file, code comments, and any generated project documentation must be written in **Simplified Chinese**.

## 2. Code & Comments
* **Code Logic:** Keep standard English syntax for Python/Shell commands/Variable names.
* **Comments & Docstrings:** Write all code comments and function documentation (docstrings) in **Simplified Chinese**.
* **String Literals:** Unless the code requires specific English strings (e.g. API keys, specific headers), use Chinese for UI output, logs, or user-facing messages where appropriate.

## 3. Override
This rule overrides any default system language settings. Always prioritize Chinese.

## 4. Technical Terminology
* Keep specific technical terms (e.g., "Transformer", "Agent", "LLM", "UnicodeEncodeError", "Pipeline") in **English** if the translation is awkward or standard industry practice prefers English.

## 5. README Format
When generating or updating `README.md`:
* Use clear H1/H2 headers in Chinese.
* Include sections: 项目简介 (Introduction), 安装说明 (Installation), 使用指南 (Usage).