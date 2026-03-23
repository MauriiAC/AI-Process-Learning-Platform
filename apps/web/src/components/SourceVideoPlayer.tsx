import { useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { ExternalLink, Loader2, Video } from "lucide-react";

import api from "@/services/api";

interface VideoJumpRequest {
  range: string;
  nonce: number;
}

interface SourceVideoPlayerProps {
  storageKey?: string | null;
  mime?: string | null;
  title?: string;
  description?: string;
  jumpToRange?: VideoJumpRequest | null;
}

interface AccessUrlResponse {
  access_url: string;
}

function getErrorMessage(error: unknown) {
  if (
    typeof error === "object" &&
    error !== null &&
    "response" in error &&
    typeof (error as { response?: { data?: { detail?: string } } }).response?.data?.detail === "string"
  ) {
    return (error as { response?: { data?: { detail?: string } } }).response?.data?.detail!;
  }
  return "No se pudo cargar el video fuente.";
}

function parseTimeToken(value: string) {
  const normalized = value.trim().toLowerCase();
  if (!normalized) return null;

  const clockMatch = normalized.match(/^(\d{1,2}):(\d{2})(?::(\d{2}))?$/);
  if (clockMatch) {
    const [, first, second, third] = clockMatch;
    if (third != null) {
      return Number(first) * 3600 + Number(second) * 60 + Number(third);
    }
    return Number(first) * 60 + Number(second);
  }

  const numeric = normalized.match(/^(\d+(?:\.\d+)?)\s*s?$/);
  if (numeric) {
    return Number(numeric[1]);
  }

  return null;
}

function parseSegmentRangeStart(range: string) {
  const normalized = range.trim().replace(/\s+/g, "");
  if (!normalized) return null;

  const [start] = normalized.split("-");
  return start ? parseTimeToken(start) : null;
}

export default function SourceVideoPlayer({
  storageKey,
  mime,
  title = "Video fuente",
  description = "Reproduce el archivo original con el que se creó esta versión del procedimiento.",
  jumpToRange,
}: SourceVideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const sectionRef = useRef<HTMLElement | null>(null);
  const { data, isLoading, isError, error } = useQuery<AccessUrlResponse>({
    queryKey: ["source-video-access-url", storageKey],
    queryFn: () => api.post("/uploads/access-url", { storage_key: storageKey }).then((response) => response.data),
    enabled: Boolean(storageKey),
    staleTime: 45 * 60 * 1000,
  });

  useEffect(() => {
    if (!jumpToRange || isLoading || isError || !data?.access_url) return;

    const targetTime = parseSegmentRangeStart(jumpToRange.range);
    const video = videoRef.current;
    if (targetTime == null || !video) return;

    sectionRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });

    const seekAndPlay = () => {
      video.currentTime = targetTime;
      void video.play().catch(() => undefined);
    };

    if (video.readyState >= 1) {
      seekAndPlay();
      return;
    }

    video.addEventListener("loadedmetadata", seekAndPlay, { once: true });
    return () => {
      video.removeEventListener("loadedmetadata", seekAndPlay);
    };
  }, [data?.access_url, isError, isLoading, jumpToRange]);

  if (!storageKey) return null;

  return (
    <section ref={sectionRef} className="rounded-3xl border border-gray-200 bg-white p-6">
      <div className="flex items-start gap-3">
        <div className="rounded-2xl bg-indigo-50 p-2.5 text-indigo-700">
          <Video className="h-5 w-5" />
        </div>
        <div>
          <h2 className="text-xl font-semibold text-gray-900">{title}</h2>
          <p className="mt-1 text-sm text-gray-500">{description}</p>
        </div>
      </div>

      <div className="mt-5 overflow-hidden rounded-2xl border border-gray-200 bg-black">
        {isLoading ? (
          <div className="flex aspect-video items-center justify-center gap-3 text-sm text-white/80">
            <Loader2 className="h-5 w-5 animate-spin" />
            Cargando video fuente...
          </div>
        ) : isError || !data?.access_url ? (
          <div className="flex aspect-video items-center justify-center px-6 text-center text-sm text-white/80">
            {getErrorMessage(error)}
          </div>
        ) : (
          <video ref={videoRef} className="aspect-video w-full" controls preload="metadata">
            <source src={data.access_url} type={mime || undefined} />
            Tu navegador no soporta la reproducción de video embebida.
          </video>
        )}
      </div>

      {data?.access_url && !isLoading && !isError && (
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm">
          <p className="text-gray-500">{storageKey.split("/").pop() || storageKey}</p>
          <a
            href={data.access_url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 font-medium text-indigo-600 hover:text-indigo-700"
          >
            Abrir en una pestaña nueva
            <ExternalLink className="h-4 w-4" />
          </a>
        </div>
      )}
    </section>
  );
}
