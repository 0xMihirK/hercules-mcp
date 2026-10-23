import { useState } from "react";
import { ArrowUpRight } from "@phosphor-icons/react/ArrowUpRight";
import { Check } from "@phosphor-icons/react/Check";
import { Copy } from "@phosphor-icons/react/Copy";
import { ChatText } from "@phosphor-icons/react/ChatText";
import { PlugsConnected } from "@phosphor-icons/react/PlugsConnected";

const SUPPORTED_CLIENTS = [
  "Claude Code",
  "Codex CLI",
  "Gemini CLI",
  "OpenCode",
  "Cursor",
  "VS Code",
  "Windsurf",
  "Hermes",
];
const brand = (name: string) => `${import.meta.env.BASE_URL}assets/brands/${name}.svg`;

export default function Setup({ prompt }: { prompt: string }) {
  const [status, setStatus] = useState("");
  const copied = status.startsWith("Prompt copied");

  async function copy() {
    try {
      await navigator.clipboard.writeText(prompt);
      setStatus("Prompt copied. Paste it into your coding agent.");
    } catch {
      setStatus("Select and copy the prompt above.");
    }
  }

  return (
    <section
      id="install"
      className="chapter wrap installation-section"
      aria-labelledby="setup-title"
    >
      <div className="installation-heading">
        <div className="installation-intro">
          <h2 id="setup-title">
            Install with
            <br />
            one prompt.
          </h2>
          <p className="installation-lead">
            One setup CLI installs, updates, or repairs Hercules and nine
            portable agent skills for your current agent while keeping
            existing preferences and evidence intact.
          </p>
          <div
            className="supported-clients"
            aria-label="Supported MCP clients"
          >
            {SUPPORTED_CLIENTS.map((client) => (
              <span key={client} className="client-chip">
                {client}
              </span>
            ))}
          </div>
          <div className="platform-inline" aria-label="Supported operating systems">
            <div className="platform-badges">
              <span className="platform-pill">
                <img src={brand("windows11-original")} width="20" height="20" alt="" />
                Windows
              </span>
              <span className="platform-pill">
                <img className="platform-logo-mono" src={brand("apple-original")} width="20" height="20" alt="" />
                macOS
              </span>
              <span className="platform-pill">
                <img className="platform-logo-mono" src={brand("linux-plain")} width="20" height="20" alt="" />
                Linux
              </span>
            </div>
            <div className="platform-meta">
              Run it where your work happens.
            </div>
          </div>
        </div>
        <div className={`installation-cta-box${copied ? " is-copied" : ""}`} data-ui>
          <div className="prompt-box-header">
            <span className="prompt-box-label">
              Canonical agent setup prompt
            </span>
            <span className="prompt-box-dots" aria-hidden="true">
              <i />
              <i />
              <i />
            </span>
          </div>
          <pre className="installation-prompt">
            {prompt}
            <span className="prompt-caret" aria-hidden="true" />
          </pre>
          <div className="installation-cta-actions">
            <button className="button primary" onClick={copy}>
              {copied ? <Check size={20} /> : <Copy size={20} />}
              {copied ? "Copied to clipboard" : "Copy installation prompt"}
            </button>
            <a
              className="button ghost"
              href="https://github.com/0xMihirK/hercules-mcp/blob/main/install.md"
            >
              Full setup guide <ArrowUpRight size={18} />
            </a>
          </div>
          {status && (
            <p className="copy-status" role="status">
              {status}
            </p>
          )}
        </div>
      </div>
      <ol className="installation-path">
        <li>
          <div className="step-top">
            <Copy size={26} />
          </div>
          <h3>Copy the prompt.</h3>
          <p>
            Use the same prompt on Windows, macOS, or Linux. Full capabilities
            by default; existing bundle selections stay unchanged.
          </p>
        </li>
        <li>
          <div className="step-top">
            <ChatText size={26} />
          </div>
          <h3>Paste into your agent.</h3>
          <p>
            Configures only your active client. The 79 topic guides load on
            demand; a cold MCP handshake does not start the Kali container.
          </p>
        </li>
        <li>
          <div className="step-top">
            <PlugsConnected size={26} />
          </div>
          <h3>Connect and verify.</h3>
          <p>
            Reload your client when instructed. Runtime image downloads and
            local container smoke tests stay under your explicit control.
          </p>
        </li>
      </ol>
      <div className="installation-bottom">
        <a
          className="text-link"
          href="https://github.com/0xMihirK/hercules-mcp/blob/main/install.md"
        >
          Read install.md specification <ArrowUpRight size={18} />
        </a>
      </div>
    </section>
  );
}
