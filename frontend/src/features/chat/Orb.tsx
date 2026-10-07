export function Orb() {
  return (
    <div className="orb-wrap" aria-hidden="true">
      <div className="orb-halo" />
      <svg className="orb" viewBox="0 0 144 144" fill="none">
        <defs>
          <radialGradient id="orb-fill">
            <stop stopColor="#74d6bb" stopOpacity=".2" />
            <stop offset="1" stopColor="#74d6bb" stopOpacity="0" />
          </radialGradient>
          <linearGradient id="orb-stroke" x1="30" y1="15" x2="120" y2="125">
            <stop stopColor="#b6f3de" />
            <stop offset=".5" stopColor="#6dccad" />
            <stop offset="1" stopColor="#576cbe" />
          </linearGradient>
        </defs>
        <circle cx="72" cy="72" r="53" fill="url(#orb-fill)" />
        <g stroke="url(#orb-stroke)" strokeWidth=".8" opacity=".8">
          <circle cx="72" cy="72" r="51" />
          <ellipse cx="72" cy="72" rx="24" ry="51" />
          <ellipse cx="72" cy="72" rx="42" ry="51" />
          <ellipse cx="72" cy="72" rx="51" ry="17" />
          <ellipse cx="72" cy="72" rx="51" ry="35" />
          <ellipse cx="72" cy="72" rx="25" ry="51" transform="rotate(55 72 72)" />
          <ellipse cx="72" cy="72" rx="25" ry="51" transform="rotate(-55 72 72)" />
          <path d="M21 72h102M72 21v102M36 36l72 72M36 108l72-72" opacity=".35" />
        </g>
        <path d="m72 52 5.3 14.7L92 72l-14.7 5.3L72 92l-5.3-14.7L52 72l14.7-5.3Z" fill="#c9f7e6" />
        <circle cx="29" cy="45" r="2.5" fill="#aaf3d7" />
        <circle cx="116" cy="96" r="2" fill="#a8b4ed" />
        <circle cx="104" cy="32" r="1.5" fill="#aaf3d7" />
      </svg>
      <span className="orb-dot orb-dot-one" />
      <span className="orb-dot orb-dot-two" />
    </div>
  );
}
