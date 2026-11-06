# README diagram marks

These marks identify compatible clients and the Docker runtime in the README
architecture diagram. They are displayed in their original colors; inclusion
does not imply endorsement.

- `claude.svg`: [Claude site icon](https://claude.ai/favicon.svg).
- `cursor.svg`: [Cursor site icon](https://cursor.com/favicon.svg).
- `codex.png`: Codex app icon, as [documented by its extractor](https://github.com/backnotprop/orchestrator/blob/main/assets/providers/README.md); see [OpenAI's brand guidance](https://openai.com/brand/).
- `hermes.png`: [Hermes Agent site icon](https://hermes-agent.nousresearch.com/assets/hermes-agent/icon.png).
- `docker.svg`: [Devicon v2.17.0](https://github.com/devicons/devicon/tree/v2.17.0/icons), under the included `LICENSE.Devicon`.

The diagram backgrounds use a static frame of the project website's procedural
smoke/hatch renderer (`website/recipe.json`). The hero uses a generated
graphite-and-copper halftone texture in `assets/readme-hero-background.jpg`.
`scripts/render_readme_art.py` embeds the backgrounds and marks in the SVGs so
GitHub does not need to fetch linked images.
