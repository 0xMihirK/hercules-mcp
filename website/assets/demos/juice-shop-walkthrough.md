# OWASP Juice Shop local walkthrough

The Hercules MCP runtime inspected only this transaction-owned Juice Shop on a Docker internal network.
No host port was published and no public target was contacted. The model narration is scripted; Hercules tool results are real.

## Verified sequence

- Nmap identified the scoped Juice Shop service on port 3000.
- A separate HTTP request confirmed the application response and retained the page under `artifacts/juice-shop-home.html`.
- Hercules opened the application in its CloakBrowser-backed browser session and inspected the accessibility snapshot.
- The welcome banner and cookie overlay were dismissed; opening the application's hidden challenge board solved the Score Board challenge, confirmed by Juice Shop itself.
- Juice Shop reported 1 of 186 challenges solved in the captured state.
- Browser evidence is retained at `artifacts/juice-shop-scoreboard.png`.

## Scope and limits

This recording shows an authorized walkthrough of the deliberately vulnerable local training app. It does not claim CAPTCHA bypass or exploitation of an external site.
CloakBrowser reduces common automation signals; bot-detection outcomes are not guaranteed.
