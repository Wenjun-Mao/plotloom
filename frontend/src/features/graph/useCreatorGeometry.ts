import { useLayoutEffect, useRef, useState } from "react";
import type { KeyboardEvent, PointerEvent } from "react";
import { workspaceHeaders, workspaceViewportTop } from "../../app/workspace/workspaceViewport";

type Preference = { width: number | null; pageY: number; chartX: number };
const initial = (): Preference => ({ width: null, pageY: 0, chartX: 0 });
function readPreference(key: string): Preference {
  try {
    const value = JSON.parse(localStorage.getItem(key) || "null");
    if (value && (value.width === null || Number.isFinite(value.width)) && Number.isFinite(value.pageY) && Number.isFinite(value.chartX)) return value;
  } catch { /* Presentation storage failure never affects authored content. */ }
  return initial();
}
export function inspectorBounds(contentWidth: number) { return { min: 300, max: Math.max(300, Math.min(520, contentWidth * .45, contentWidth - 498)), automatic: contentWidth >= 1120 ? 380 : 300 }; }

export function useCreatorGeometry(projectId: string, selectedY: number | undefined) {
  const key = `plotloom:creator-presentation:v1:${projectId}`;
  const layout = useRef<HTMLDivElement>(null), inspector = useRef<HTMLElement>(null), divider = useRef<HTMLDivElement>(null), chart = useRef<HTMLDivElement>(null);
  const preference = useRef(readPreference(key));
  const storedPosition = useRef(false);
  const gesture = useRef<{ pointerId: number; startX: number; startWidth: number; original: number | null } | null>(null);
  const [chartWidth, setChartWidth] = useState(600);
  const [desktop, setDesktop] = useState(window.innerWidth >= 1280);
  const [ready, setReady] = useState(false);
  const selected = useRef(selectedY); selected.current = selectedY;
  const bounds = () => inspectorBounds(layout.current?.clientWidth ?? 1000);
  const effective = () => { const range = bounds(); return Math.max(range.min, Math.min(range.max, preference.current.width ?? range.automatic)); };
  const persist = () => {
    try { localStorage.setItem(key, JSON.stringify({ ...preference.current, width: gesture.current ? gesture.current.original : preference.current.width, pageY: window.scrollY, chartX: chart.current?.scrollLeft ?? 0 })); } catch { /* Optional presentation preference. */ }
  };
  const place = () => {
    const element = layout.current, panel = inspector.current, handle = divider.current;
    if (!element || !panel || !handle) return;
    const width = effective(); element.style.setProperty("--creator-inspector-width", `${width}px`);
    handle.setAttribute("aria-valuenow", String(Math.round(width)));
    handle.setAttribute("aria-valuemax", String(Math.floor(bounds().max)));
    const rect = element.getBoundingClientRect();
    const top = Math.max(rect.top + 8, workspaceViewportTop() + 8), bottom = Math.min(rect.bottom - 8, window.innerHeight - 8);
    const available = Math.max(0, bottom - top), height = Math.min(available, window.innerHeight * .85);
    const centre = rect.top + (selected.current ?? 56);
    const panelTop = Math.max(top, Math.min(bottom - height, centre - height / 2)) - rect.top;
    panel.style.top = `${Math.max(8, panelTop)}px`; panel.style.height = `${height}px`;
    handle.style.top = panel.style.top; handle.style.height = panel.style.height;
  };
  const cancel = () => { if (!gesture.current) return; preference.current.width = gesture.current.original; gesture.current = null; place(); };
  useLayoutEffect(() => {
    preference.current = readPreference(key);
    try { storedPosition.current = localStorage.getItem(key) !== null; } catch { storedPosition.current = false; }
    const resize = () => { setDesktop(window.innerWidth >= 1280); place(); setChartWidth(chart.current?.clientWidth ?? 600); };
    const scroll = () => { place(); persist(); };
    const cancelKey = (event: globalThis.KeyboardEvent) => {
      if (!gesture.current || !["Escape", "Tab"].includes(event.key)) return;
      if (event.key === "Escape") event.preventDefault();
      cancel();
    };
    const observer = new ResizeObserver(resize); if (layout.current) observer.observe(layout.current); if (chart.current) observer.observe(chart.current);
    for (const header of workspaceHeaders()) observer.observe(header);
    window.addEventListener("resize", resize); window.addEventListener("scroll", scroll, { passive: true }); window.addEventListener("keydown", cancelKey); window.addEventListener("blur", cancel);
    chart.current?.addEventListener("scroll", persist, { passive: true }); resize();
    if (chart.current) chart.current.scrollLeft = preference.current.chartX;
    const restore = requestAnimationFrame(() => { window.scrollTo(0, preference.current.pageY); setReady(true); });
    return () => { cancelAnimationFrame(restore); cancel(); observer.disconnect(); window.removeEventListener("resize", resize); window.removeEventListener("scroll", scroll); window.removeEventListener("keydown", cancelKey); window.removeEventListener("blur", cancel); chart.current?.removeEventListener("scroll", persist); };
  }, [key]);
  useLayoutEffect(place, [selectedY, chartWidth]);
  const adjust = (width: number | null) => { preference.current.width = width; place(); if (!gesture.current) persist(); };
  const pointerDown = (event: PointerEvent<HTMLDivElement>) => { if (event.button !== 0) return; event.preventDefault(); gesture.current = { pointerId: event.pointerId, startX: event.clientX, startWidth: effective(), original: preference.current.width }; event.currentTarget.setPointerCapture(event.pointerId); };
  const pointerMove = (event: PointerEvent<HTMLDivElement>) => { if (!gesture.current || event.pointerId !== gesture.current.pointerId) return; const range = bounds(); adjust(Math.max(range.min, Math.min(range.max, gesture.current.startWidth - event.clientX + gesture.current.startX))); };
  const pointerUp = (event: PointerEvent<HTMLDivElement>) => { if (!gesture.current || event.pointerId !== gesture.current.pointerId) return; gesture.current = null; persist(); event.currentTarget.releasePointerCapture(event.pointerId); };
  const keyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const range = bounds(), step = event.shiftKey ? 50 : 10;
    const value = event.key === "ArrowLeft" ? effective() + step : event.key === "ArrowRight" ? effective() - step : event.key === "Home" ? range.min : event.key === "End" ? range.max : null;
    if (value !== null) { event.preventDefault(); adjust(Math.max(range.min, Math.min(range.max, value))); }
  };
  return { layout, inspector, divider, chart, chartWidth, desktop, ready, storedPosition, place, dividerEvents: { onPointerDown: pointerDown, onPointerMove: pointerMove, onPointerUp: pointerUp, onPointerCancel: cancel, onLostPointerCapture: cancel, onBlur: cancel, onKeyDown: keyDown, onDoubleClick: () => adjust(null) } };
}
