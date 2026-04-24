# JAM SDK for C3

## Using the SDK in Your Project (Recommended for IDE suggestions)

Add the SDK as a C3 library dependency — your editor/LSP will provide full autocompletion for all `jam::` modules.

```bash
mkdir -p lib
git clone https://github.com/DrEverr/jamc3.c3l.git lib/jamc3.c3l
```

Then create your `project.json`:

```json
{
  "dependency-search-paths": ["lib"],
  "dependencies": ["jamc3"],
  "sources": ["src/**"],
  "use-stdlib": false,
  "link-libc": false
}
```

You can now `import jam::types`, `import jam::service`, etc. with full IDE suggestions.
