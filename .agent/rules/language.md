---
trigger: always_on
---

# Language & Communication Protocol

## 1. Output Language
You must strictly use **Simplified Chinese (简体中文)** for all interactions, including:
* **Chat Responses:** All replies to the user.
* **Walkthroughs & Planning:** The step-by-step reasoning and plans must be written in Chinese.
* **Implementation Explanations:** When explaining code or writing commit messages.

## 2. Code & Comments
* **Code Logic:** Keep standard English syntax for Python/Shell commands.
* **Comments & Docstrings:** Write all code comments and function documentation (docstrings) in **Simplified Chinese**.
* **String Literals:** Unless the code requires specific English strings, use Chinese for UI output or logs where appropriate.

## 3. Override
This rule overrides any default system language settings. Always prioritize Chinese.

## 4. Technical Terminology
* Keep specific technical terms (e.g., "Transformer", "Agent", "LLM", "UnicodeEncodeError") in **English** if the translation is awkward or standard industry practice prefers English.