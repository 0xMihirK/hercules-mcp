import { useState } from "react";
import { ArrowUpRight } from "@phosphor-icons/react/ArrowUpRight";
import { Check } from "@phosphor-icons/react/Check";
import { Copy } from "@phosphor-icons/react/Copy";
import { ChatText } from "@phosphor-icons/react/ChatText";
import { PlugsConnected } from "@phosphor-icons/react/PlugsConnected";
import { AppleLogo } from "@phosphor-icons/react/AppleLogo";
import { WindowsLogo } from "@phosphor-icons/react/WindowsLogo";
import { LinuxLogo } from "@phosphor-icons/react/LinuxLogo";

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
            One setup CLI installs, updates, or repairs Hercules for your
            current agent while keeping existing preferences and evidence
            intact.
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
                <WindowsLogo size={18} weight="fill" />
                Windows
              </span>
              <span className="platform-pill">
                <AppleLogo size={18} weight="fill" />
                macOS
              </span>
              <span className="platform-pill">
                <LinuxLogo size={18} weight="fill" />
                Linux
              </span>
            </div>
            <div className="platform-meta">
              <span className="platform-dot" aria-hidden="true" />
              <span>Same STDIO MCP host server · Docker on each system</span>
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
            Configures only your active client. Host setup verifies a cold MCP
            handshake without starting the Kali container.
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
        <p>
          Requires Git, <code>uv</code>, and a terminal-capable STDIO MCP agent
          for host setup; Docker when preparing or starting the Kali runtime.
        </p>
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
