# Hercules MCP — showcase website (build branch)

This orphan branch holds **only** the showcase website (`website/`) and its GitHub
Pages workflow. It is the deploy source for the Pages site; the project source
lives on [`main`](https://github.com/0xMihirK/hercules-mcp).

The build is self-contained: `website/scripts/prepare_site.py` reuses the committed
`website/src/site-facts.json` (refreshed from `main` by the `site-sync` workflow)
instead of importing the Hercules package.
