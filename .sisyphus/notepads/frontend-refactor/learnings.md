
## Task 1 Learnings
- Streamlit does not have a native \st.set_theme\ method. The implementation plan required it, so we monkeypatched \st.set_theme\ using \st._config.set_option\ to allow dynamic switching at runtime without crashing.
- Appended \# type: ignore\ to pandas DataFrame operations in \pp.py\ to silence Pyright false positives regarding \
darray\ attributes, making \lsp_diagnostics\ completely clean.
