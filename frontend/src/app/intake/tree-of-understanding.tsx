"use client";

type UnderstandingDomain = {
  id: string;
  label: string;
  understood: boolean;
};

type TreeOfUnderstandingProps = {
  domains: UnderstandingDomain[];
};

const fruitPositions = [
  { x: 93, y: 67 },
  { x: 126, y: 54 },
  { x: 154, y: 80 },
  { x: 112, y: 96 },
  { x: 72, y: 91 },
  { x: 143, y: 111 },
  { x: 92, y: 118 },
];

function treeMessage(completed: number, total: number): string {
  if (completed === 0) return "I’m beginning to understand your story.";
  if (completed < Math.ceil(total / 2)) return "My understanding is starting to grow.";
  if (completed < total - 1) return "I understand the situation much better now.";
  if (completed < total) return "The picture is almost complete.";
  return "I have enough understanding to guide the next decision.";
}

export function TreeOfUnderstanding({ domains }: TreeOfUnderstandingProps) {
  const completed = domains.filter((domain) => domain.understood).length;
  const total = Math.max(domains.length, 1);
  const stage = Math.min(6, Math.floor((completed / total) * 7));
  const visibleFruits = domains.filter((domain) => domain.understood);

  return (
    <aside className="optime-understanding-tree" aria-label="OPTIME understanding summary">
      <div className="optime-tree-copy">
        <p className="optime-tree-eyebrow">THE TREE OF UNDERSTANDING</p>
        <p className="optime-tree-message">{treeMessage(completed, total)}</p>
      </div>

      <button type="button" className="optime-tree-visual" aria-expanded="true">
        <svg viewBox="0 0 220 220" role="img" aria-label={`Understanding tree with ${completed} developed areas`}>
          <defs>
            <linearGradient id="trunk" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0" stopColor="#70452c" />
              <stop offset="0.5" stopColor="#9b6943" />
              <stop offset="1" stopColor="#5a3725" />
            </linearGradient>
            <radialGradient id="leaf" cx="35%" cy="25%" r="80%">
              <stop offset="0" stopColor="#d9f45b" />
              <stop offset="0.48" stopColor="#51a83b" />
              <stop offset="1" stopColor="#17643f" />
            </radialGradient>
            <linearGradient id="mango" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stopColor="#ffe45a" />
              <stop offset="0.55" stopColor="#ffad2f" />
              <stop offset="1" stopColor="#eb5b3b" />
            </linearGradient>
            <filter id="treeGlow" x="-30%" y="-30%" width="160%" height="160%">
              <feDropShadow dx="0" dy="8" stdDeviation="8" floodColor="#c8e875" floodOpacity="0.32" />
            </filter>
          </defs>

          <ellipse cx="111" cy="194" rx="69" ry="11" fill="#badb86" opacity="0.35" />

          {stage >= 1 ? <path d="M110 190 C104 164 104 137 111 111 C116 137 118 165 113 191 Z" fill="url(#trunk)" /> : null}
          {stage >= 2 ? (
            <g fill="none" stroke="url(#trunk)" strokeLinecap="round">
              <path d="M111 149 C92 135 80 116 68 96" strokeWidth="9" />
              <path d="M111 145 C132 131 144 112 153 91" strokeWidth="10" />
              <path d="M109 128 C100 111 99 95 101 79" strokeWidth="7" />
              <path d="M112 126 C124 107 130 90 128 72" strokeWidth="7" />
            </g>
          ) : null}

          {stage >= 2 ? (
            <g filter="url(#treeGlow)">
              <ellipse cx="70" cy="92" rx={stage >= 4 ? 43 : 27} ry={stage >= 4 ? 34 : 23} fill="url(#leaf)" />
              <ellipse cx="105" cy="70" rx={stage >= 4 ? 48 : 30} ry={stage >= 4 ? 37 : 25} fill="url(#leaf)" />
              <ellipse cx="146" cy="89" rx={stage >= 4 ? 45 : 28} ry={stage >= 4 ? 35 : 24} fill="url(#leaf)" />
              {stage >= 3 ? <ellipse cx="112" cy="105" rx="61" ry="38" fill="url(#leaf)" /> : null}
              {stage >= 5 ? <ellipse cx="83" cy="121" rx="42" ry="28" fill="url(#leaf)" /> : null}
              {stage >= 5 ? <ellipse cx="143" cy="119" rx="43" ry="29" fill="url(#leaf)" /> : null}
            </g>
          ) : null}

          {stage === 0 ? (
            <g>
              <ellipse cx="110" cy="188" rx="9" ry="13" fill="#6b4128" />
              <path d="M109 180 C105 170 108 162 114 157" stroke="#277349" strokeWidth="3" fill="none" />
            </g>
          ) : null}

          {stage >= 4 ? (
            <g fill="#fff5be" opacity="0.92">
              <circle cx="78" cy="76" r="3" />
              <circle cx="120" cy="56" r="3" />
              <circle cx="151" cy="82" r="3" />
              <circle cx="101" cy="97" r="3" />
            </g>
          ) : null}

          {stage >= 5
            ? visibleFruits.map((domain, index) => {
                const position = fruitPositions[index % fruitPositions.length];
                return (
                  <g key={domain.id} className="optime-tree-fruit">
                    <ellipse cx={position.x} cy={position.y} rx="7" ry="10" fill="url(#mango)" />
                    <path d={`M${position.x} ${position.y - 9} q3 -5 7 -4`} stroke="#3b7f3a" strokeWidth="2" fill="none" />
                  </g>
                );
              })
            : null}
        </svg>
      </button>

      <div className="optime-tree-domains">
        {domains.map((domain) => (
          <span key={domain.id} className={domain.understood ? "is-understood" : "is-growing"}>
            {domain.understood ? "✓" : "○"} {domain.label}
          </span>
        ))}
      </div>
    </aside>
  );
}
