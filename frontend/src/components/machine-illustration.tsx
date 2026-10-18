export function MachineIllustration({
  compact = false,
}: {
  compact?: boolean;
}) {
  return (
    <svg
      viewBox="0 0 500 340"
      role="img"
      aria-label="Stylized CNC machining center, synthetic illustration"
      className={compact ? "machine-art compact" : "machine-art"}
    >
      <defs>
        <linearGradient id="body" x1="0" x2="1" y2="1">
          <stop stopColor="var(--text)" />
          <stop offset="1" stopColor="var(--machine-metal-shade)" />
        </linearGradient>
        <linearGradient id="side" x1="0" x2="1">
          <stop stopColor="var(--machine-metal-shade)" />
          <stop offset="1" stopColor="var(--panel-hover)" />
        </linearGradient>
        <linearGradient id="glass" x1="0" x2="1" y2="1">
          <stop stopColor="var(--bg)" />
          <stop offset="1" stopColor="var(--border)" />
        </linearGradient>
      </defs>
      <ellipse
        cx="255"
        cy="301"
        rx="178"
        ry="18"
        fill="var(--bg)"
        opacity=".5"
      />
      <path d="M93 83 154 48 407 70 348 106Z" fill="var(--machine-metal)" />
      <path d="m348 106 59-36v209l-59 30Z" fill="url(#side)" />
      <path d="M93 83 348 106v203L93 284Z" fill="url(#body)" />
      <path d="m103 103 232 20v25l-232-20Z" fill="var(--border)" />
      <path
        d="m104 130 147 13v126l-147-13Z"
        fill="var(--machine-metal-shade)"
      />
      <path
        d="m115 141 121 11v100l-121-11Z"
        fill="url(#glass)"
        stroke="var(--machine-metal-shade)"
        strokeWidth="5"
      />
      <path
        d="m175 147 1 98M117 207l118 9"
        stroke="var(--machine-metal-shade)"
        strokeWidth="3"
      />
      <path d="m153 174 58 5v45l-58-5Z" fill="var(--border)" />
      <path d="m173 168 17 1v45l-17-1Z" fill="var(--machine-metal-shade)" />
      <path d="m178 210 7 1v17l-7-1Z" fill="var(--machine-metal)" />
      <path d="m130 229 91 8v9l-91-8Z" fill="var(--machine-metal-shade)" />
      <path d="m244 151 5 1v102l-5-1Z" fill="var(--text)" />
      <path d="m269 151 54 5v92l-54-5Z" fill="var(--border)" />
      <path d="m277 161 37 3v33l-37-3Z" fill="var(--bg)" />
      <path
        d="m281 174 27 2m-27 6 17 1m-17 7 23 2"
        stroke="var(--machine-metal)"
        strokeWidth="2"
      />
      {[0, 1, 2, 3].map((row) =>
        [0, 1, 2, 3].map((col) => (
          <rect
            key={`${row}-${col}`}
            x={278 + col * 9}
            y={205 + row * 8 + col * 0.6}
            width="5"
            height="4"
            rx="1"
            fill="var(--machine-metal)"
          />
        )),
      )}
      <circle cx="314" cy="240" r="5" fill="var(--danger)" />
      <path d="m103 267 232 20v13l-232-20Z" fill="var(--border)" />
      <path
        d="m109 284 28 3v12l-28-2Zm193 17 29 3v12l-29-2Z"
        fill="var(--bg)"
      />
      <path d="m371 108 22-11v146l-22 11Z" fill="var(--border)" />
      <path d="m378 120 8-4v113l-8 4Z" fill="var(--border)" />
      <path
        d="M319 68V38"
        stroke="var(--machine-metal-shade)"
        strokeWidth="6"
      />
      <rect
        x="313"
        y="24"
        width="12"
        height="14"
        rx="3"
        fill="var(--success)"
      />
      <rect x="313" y="38" width="12" height="9" rx="2" fill="var(--border)" />
      <text
        x="114"
        y="120"
        fill="var(--text)"
        fontSize="11"
        fontWeight="700"
        letterSpacing="3"
        transform="rotate(5 114 120)"
      >
        SHIFT / CNC
      </text>
      <path d="m95 288-25 16m279 6 27 13" stroke="var(--border)" />
      <circle cx="69" cy="304" r="3" fill="var(--machine-metal-shade)" />
      <circle cx="402" cy="324" r="3" fill="var(--machine-metal-shade)" />
    </svg>
  );
}
