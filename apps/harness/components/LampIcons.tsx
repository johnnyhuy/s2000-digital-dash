/** White-on-transparent ISO pictograms. Tint with currentColor. */

import type { ReactNode } from "react";

/** `x` / `y` are the plate centre when nested inside another SVG. */
type IconProps = { className?: string; width?: number; x?: number; y?: number; fill?: string };

function Plate({
  className,
  width,
  x,
  y,
  fill = "currentColor",
  viewBox = "0 0 64 48",
  children,
}: IconProps & { viewBox?: string; children: ReactNode }) {
  const height = width ? width * 0.75 : undefined;
  return (
    <svg
      className={className}
      viewBox={viewBox}
      width={width}
      height={height}
      x={x !== undefined && width ? x - width / 2 : undefined}
      y={y !== undefined && height ? y - height / 2 : undefined}
      fill={fill}
      aria-hidden
    >
      {children}
    </svg>
  );
}

export function TurnLeftIcon(props: IconProps) {
  return (
    <Plate {...props}>
      <path d="M42.6 8.4 8.2 24l34.4 15.6v-8.2H56V16.6H42.6z" />
    </Plate>
  );
}

export function TurnRightIcon(props: IconProps) {
  return (
    <Plate {...props}>
      <path d="M21.4 8.4v8.2H8v15.2h13.4v8.2L55.8 24z" />
    </Plate>
  );
}

export function HighBeamIcon(props: IconProps) {
  return (
    <Plate {...props}>
      <rect x="3.4" y="12.4" width="22.8" height="3.5" rx="0.35" />
      <rect x="3.4" y="22.25" width="22.8" height="3.5" rx="0.35" />
      <rect x="3.4" y="32.1" width="22.8" height="3.5" rx="0.35" />
      <path
        fillRule="evenodd"
        d="M32.6 7.6h6.2C54.4 7.6 61.2 14.6 61.2 24S54.4 40.4 38.8 40.4h-6.2V7.6z M36.8 12.2v23.6h2.8c11.6 0 16.4-5.5 16.4-11.8S51.2 12.2 39.6 12.2h-2.8z"
      />
    </Plate>
  );
}

export function BatteryIcon(props: IconProps) {
  return (
    <Plate {...props}>
      <rect x="18.2" y="4.6" width="9.6" height="7" rx="0.7" />
      <rect x="36.2" y="4.6" width="9.6" height="7" rx="0.7" />
      <path fillRule="evenodd" d="M9.2 12.2h45.6v31.2H9.2z M14.4 17.4h35.2v20.8H14.4z" />
      <rect x="18.8" y="25.4" width="10.8" height="3.1" />
      <rect x="22.65" y="21.55" width="3.1" height="10.8" />
      <rect x="34.6" y="25.4" width="10.8" height="3.1" />
    </Plate>
  );
}

export function OilIcon(props: IconProps) {
  return (
    <Plate {...props}>
      <path
        fillRule="evenodd"
        d="M4.4 26.2c0-9.4 6.8-16.4 17-16.4h5.6v4.8H22c-6.2 0-10.2 4.2-10.2 11.6S15.8 37.8 22 37.8h5v4.8h-5.6C11.2 42.6 4.4 35.6 4.4 26.2z"
      />
      <rect x="28.4" y="10.4" width="11.2" height="4.6" rx="0.6" />
      <path fillRule="evenodd" d="M20.6 15.2h26.2v22.2H20.6z M25.2 19.8h17v13H25.2z" />
      <path
        fillRule="evenodd"
        d="M45.2 16.2 56.6 5.8l5 5.2-8.8 8z M48.8 17.6 56.6 10.6l1.7 1.8-6.2 5.6z"
      />
      <path d="M57.4 14.4c0 3.2 2.2 5.7 4.3 5.7s4.3-2.5 4.3-5.7c0-2.5-1.8-5.5-4.3-8.5-2.5 3-4.3 6-4.3 8.5z" />
    </Plate>
  );
}

const CHECK_HOLES =
  "M16.2 22.2h5.1v2.05h-3.05v4.5h3.05v2.05h-5.1zM22.2 22.2h2.05v3.35h1.7V22.2h2.05v8.6h-2.05v-3.2h-1.7v3.2H22.2zM29.1 22.2h5.05v2.05h-3v1.55h2.45v1.9H31.15v1.05h3v2.05h-5.05zM35.3 22.2h5.1v2.05h-3.05v4.5h3.05v2.05h-5.1zM41.5 22.2h2.1v3.15l2.55-3.15h2.35L45.3 26.4l3.35 4.4h-2.45l-2.05-2.7v2.7h-2.1z";

export function CelIcon(props: IconProps) {
  return (
    <Plate {...props}>
      <path
        fillRule="evenodd"
        d={`M16.4 8.8h19.2c1.7 0 3.15 1.05 3.7 2.6l1.85 5.2h8.4l4.4-4.7h4.8v6.4h3.1v12.4h-3.1v6.6H8.2v-6.6H2.6V25.8h5.2v-4h6.8L15 11.4c.5-1.55 1.95-2.6 3.4-2.6z ${CHECK_HOLES}`}
      />
    </Plate>
  );
}

export function ImmobilizerIcon(props: IconProps) {
  return (
    <Plate {...props}>
      <path fillRule="evenodd" d="M17.6 5.2a16.6 16.6 0 1 0 .02 0zm0 7.2a9.4 9.4 0 1 0 .02 0z" />
      <rect x="30.6" y="19.4" width="30.2" height="7.8" rx="1.4" />
      <rect x="45.6" y="27" width="4.8" height="7.4" rx="0.7" />
      <rect x="52.2" y="27" width="4.8" height="10.2" rx="0.7" />
      <rect x="58.8" y="27" width="4.8" height="13.2" rx="0.7" />
    </Plate>
  );
}

export function SeatbeltIcon(props: IconProps) {
  return (
    <Plate {...props}>
      <circle cx="32" cy="7.8" r="6.2" />
      <path d="M29.4 13.4h5.2v3.2h-5.2z" />
      <path
        fillRule="evenodd"
        d="M18.2 18.2 25.8 16.4 29.2 19.4h5.6l3.4-3 7.6 1.8-2.4 26.6H20.6z M21.6 15.4 47.4 45h-8.8L20.2 22.2z"
      />
    </Plate>
  );
}

export function DoorIcon(props: IconProps) {
  return (
    <Plate {...props}>
      <path
        fillRule="evenodd"
        d="M24.8 2.4h14.4c2.05 0 3.9 1.15 4.8 3L48 11.8v25.8c0 1.75-1.05 3.35-2.7 4.35L38.4 46H25.6l-6.9-4.05c-1.65-1-2.7-2.6-2.7-4.35V11.8L20 5.4c.9-1.85 2.75-3 4.8-3z M27.4 8.4h9.2v8.8h-9.2z"
      />
      <path d="M18.2 20.6 2.8 28.6l3.4 5.8 13.4-7.1z" />
      <path d="M45.8 20.6 61.2 28.6l-3.4 5.8-13.4-7.1z" />
    </Plate>
  );
}

export const PICTOGRAMS = {
  turn_l: TurnLeftIcon,
  turn_r: TurnRightIcon,
  high_beam: HighBeamIcon,
  battery: BatteryIcon,
  oil: OilIcon,
  cel: CelIcon,
  immobilizer: ImmobilizerIcon,
  seatbelt: SeatbeltIcon,
  door: DoorIcon,
} as const;
