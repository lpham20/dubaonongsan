import { useEffect, useState } from "react";
import { AlertTriangle, BadgeCheck, Clock3 } from "./icons";

type ScrapeHealth = {
  status: "ok" | "stale" | "worker_dead" | "no_scrape_ever";
  last_success_at?: string;
  age_minutes?: number;
};

async function readHealthResponse(res: Response) {
  const contentType = res.headers.get("content-type") ?? "";
  if (!contentType.toLowerCase().includes("application/json")) {
    throw new Error("Invalid health response");
  }
  return res.json();
}

export function FreshnessBanner() {
  const [health, setHealth] = useState<ScrapeHealth | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function tick() {
      try {
        const apiBase = import.meta.env.VITE_API_BASE_URL || "https://api.dubaonongsan.com";
        const res = await fetch(`${apiBase}/api/v1/health/scrape`);
        const body = await readHealthResponse(res);
        if (cancelled) return;
        setHealth(
          res.ok
            ? { status: body.status ?? "ok", ...body }
            : { status: body?.detail?.status ?? "worker_dead", ...body?.detail }
        );
      } catch {
        if (!cancelled) setHealth({ status: "worker_dead" });
      }
    }

    void tick();
    const id = window.setInterval(tick, 5 * 60 * 1000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  if (!health) return null;

  if (health.status === "ok") {
    const age = health.age_minutes ?? 0;
    const human =
      age < 60
        ? `${Math.round(age)} phút trước`
        : age < 24 * 60
          ? `${Math.round(age / 60)} giờ trước`
          : `${Math.round(age / (24 * 60))} ngày trước`;
    const date = health.last_success_at ? new Date(health.last_success_at) : null;
    const timeStr = date
      ? new Intl.DateTimeFormat("vi-VN", {
          hour: "2-digit",
          minute: "2-digit",
          day: "2-digit",
          month: "2-digit"
        }).format(date)
      : "-";
    return (
      <div className="freshness-banner ok">
        <BadgeCheck size={14} />
        <span>
          <strong>Cập nhật lúc {timeStr}</strong> ({human})
        </span>
      </div>
    );
  }

  if (health.status === "stale") {
    return (
      <div className="freshness-banner stale">
        <Clock3 size={14} />
        <span>Dữ liệu cũ - quá trình cập nhật đang chậm</span>
      </div>
    );
  }

  return (
    <div className="freshness-banner dead">
      <AlertTriangle size={14} />
      <span>Hệ thống cập nhật giá đang bảo trì. Dữ liệu hiển thị là lần cập nhật gần nhất.</span>
    </div>
  );
}
