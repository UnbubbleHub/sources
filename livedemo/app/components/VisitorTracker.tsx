"use client";

import { useEffect, useRef } from "react";
import { trackVisit } from "@/app/analytics";

export function VisitorTracker() {
  const tracked = useRef(false);

  useEffect(() => {
    if (tracked.current) return;
    tracked.current = true;
    if (window.location.pathname.startsWith("/admin")) return;
    trackVisit(window.location.pathname);
  }, []);

  return null;
}
