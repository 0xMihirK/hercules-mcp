# Website content review

Reviewed on 2026-10-15 for technical and nontechnical readers. The page should explain what Hercules provides, how the agent uses it, and how to begin setup.

## Findings and edits

| Finding | Edit |
| --- | --- |
| “Keep the runtime explicit” explains an implementation rule without its meaning. | The hero now says tools run in a Kali Docker container and start when needed. The lifecycle explains that connecting leaves the container stopped. |
| “Owned runtime,” “independent runtime ownership,” and “bounded output” add jargon. | Use container, session, output limit, and the action each person or agent takes. Define a container as a separate software environment, and expand MCP in the portability section. |
| Repeated “verified,” “retained,” and “evidence” obscure the investigation. | Describe the observation: an unknown service, AtlasLab headers, a missing page, a rejected password, a failed key, or a successful health check. |
| “Your choice of agent stays yours” and the self-answered website question add little information. | State STDIO MCP compatibility and show the actual example's confirmed finding and rejected lead. |
| The recovery summary could imply that the service went down and recovered. | State the observed timeout and successful independent health check. The timeout received zero bytes; no recovered partial response is claimed. |
| Certificate validation and browser trust could be conflated. | State that validation used the supplied lab authority, while the browser reported a trust error. The HTTP screenshot is not presented as HTTPS success. |
| Setup could sound like an unconditional one-click install. | One prompt starts guided setup. The agent checks prerequisites, asks which tools are needed, and configures the client. The canonical prompt stays unchanged. |
| CTF and filtering terminology was assumed. | Expand capture-the-flag and MCP; explain a hidden answer, scanner noise, tool-specific filters, and separate response-size limits. |
| Generic artifact labels could suggest the log was reconciled before the full-file count existed. | Labels now follow the actual available artifact: current checks, full log count, packet clues, or flag verification. Reports retain their verified availability gate. |
| Social metadata led with a hard-coded tool count and vague session wording. | Describe Docker tools, compatible agents, output filters, and guided installation. |

## Fact checks

Product claims were checked against the committed README, installation contract, output filters, and session/container documentation. Narrative edits were checked against the retained native sessions and lab artifacts, including:

- service scans that cannot confidently identify the software, followed by AtlasLab response headers;
- a backup page returning 404 and independent browser confirmation of debug data;
- certificate validation using the lab authority and a browser certificate-authority error;
- a successful browser login followed by a separate 401 incorrect-password response;
- a web challenge's missing draft session, discovered header, and verified flag;
- a zero-byte timed-out request and a successful health request;
- a remediation comparison confirming the closed debug page and expected security headers.

Claims stay within these observations. An open port or exploit reference is not presented as a confirmed vulnerability. Output filtering is distinct from response-size limits; no numerical savings claim is introduced. One prompt guides installation rather than removing prerequisite or configuration choices.

The edited website and `src/showcase-content.json` contain the full revised copy. Captured terminal pixels, raw transcripts, report artifacts, call ordinals, availability timestamps, and the canonical installation prompt retain their original content. The hero headline, agent introduction, theme, and typography remain.
