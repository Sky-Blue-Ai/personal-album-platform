"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type Props = { src: string; alt: string; width: number; height: number };

const MIN = 1;
const MAX = 5;

export default function Viewer({ src, alt, width, height }: Props) {
  const boxRef = useRef<HTMLDivElement | null>(null);
  const [scale, setScale] = useState(1);
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const drag = useRef<{ x: number; y: number; ox: number; oy: number } | null>(null);

  const clamp = useCallback((s: number, x: number, y: number) => {
    const box = boxRef.current;
    if (!box) return { x, y };
    const w = box.clientWidth;
    const h = box.clientHeight;
    const minX = w - w * s;
    const minY = h - h * s;
    return {
      x: Math.min(0, Math.max(minX, x)),
      y: Math.min(0, Math.max(minY, y)),
    };
  }, []);

  const zoomTo = useCallback(
    (next: number, cx?: number, cy?: number) => {
      const box = boxRef.current;
      const s = Math.min(MAX, Math.max(MIN, next));
      if (!box) return setScale(s);
      const w = box.clientWidth;
      const h = box.clientHeight;
      const px = cx ?? w / 2;
      const py = cy ?? h / 2;
      setPos((prev) => {
        // 以光标为锚点缩放
        const nx = px - ((px - prev.x) * s) / scale;
        const ny = py - ((py - prev.y) * s) / scale;
        return clamp(s, nx, ny);
      });
      setScale(s);
    },
    [clamp, scale],
  );

  useEffect(() => {
    const box = boxRef.current;
    if (!box) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const rect = box.getBoundingClientRect();
      const factor = Math.exp(-e.deltaY * 0.0015);
      zoomTo(scale * factor, e.clientX - rect.left, e.clientY - rect.top);
    };
    box.addEventListener("wheel", onWheel, { passive: false });
    return () => box.removeEventListener("wheel", onWheel);
  }, [scale, zoomTo]);

  const onPointerDown = (e: React.PointerEvent) => {
    if (scale <= 1) return;
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    drag.current = { x: e.clientX, y: e.clientY, ox: pos.x, oy: pos.y };
    setDragging(true);
  };

  const onPointerMove = (e: React.PointerEvent) => {
    const d = drag.current;
    if (!d) return;
    const next = clamp(scale, d.ox + (e.clientX - d.x), d.oy + (e.clientY - d.y));
    setPos(next);
  };

  const endDrag = () => {
    drag.current = null;
    setDragging(false);
  };

  const reset = () => {
    setScale(1);
    setPos({ x: 0, y: 0 });
  };

  const toggle = () => {
    if (scale > 1.05) return reset();
    zoomTo(2.6);
  };

  return (
    <div
      className={`viewer${dragging ? " dragging" : ""}`}
      ref={boxRef}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={endDrag}
      onPointerCancel={endDrag}
      onDoubleClick={toggle}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt={alt}
        width={width}
        height={height}
        draggable={false}
        style={{ transform: `translate(${pos.x}px, ${pos.y}px) scale(${scale})` }}
      />
      <div className="hint">滚轮 / 双指缩放 · 双击切换 · 拖拽平移</div>
      <div className="tools">
        <button onClick={() => zoomTo(scale / 1.4)} aria-label="缩小">
          −
        </button>
        <button onClick={() => zoomTo(scale * 1.4)} aria-label="放大">
          +
        </button>
        <button onClick={reset}>复位</button>
        <button onClick={() => zoomTo(MAX)}>1:1</button>
      </div>
    </div>
  );
}
