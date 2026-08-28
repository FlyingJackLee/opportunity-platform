import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";
import type {
  EventCreate,
  EventCreateResponse,
  EventDetail,
  EventItem,
  RunStatusResponse,
} from "./types";

/** Read-only monitoring endpoints -- doesn't fit createResourceHooks (no
 * create/update/status-toggle, and the detail/run shapes are nested rather
 * than flat CRUD rows). */
export function useEvents() {
  return useQuery({
    queryKey: ["events", "list"],
    queryFn: () => apiFetch<EventItem[]>("/api/v1/events"),
  });
}

export function useEvent(eventId: string | null) {
  return useQuery({
    queryKey: ["events", "detail", eventId],
    queryFn: () => apiFetch<EventDetail>(`/api/v1/events/${eventId}`),
    enabled: eventId !== null,
  });
}

export function useRun(runId: string | null) {
  return useQuery({
    queryKey: ["runs", runId],
    queryFn: () => apiFetch<RunStatusResponse>(`/api/v1/runs/${runId}`),
    enabled: runId !== null,
  });
}

export function useCreateEvent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: EventCreate) => apiFetch<EventItem>("/api/v1/events", { method: "POST", body }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["events"] }),
  });
}

export function useAnalyzeEvent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (eventId: string) =>
      apiFetch<EventCreateResponse>(`/api/v1/events/${eventId}/analyze`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["events"] }),
  });
}

export function useReanalyzeEvent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (eventId: string) =>
      apiFetch<EventCreateResponse>(`/api/v1/events/${eventId}/reanalyze`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["events"] }),
  });
}

export function useDeleteEvent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (eventId: string) => apiFetch<void>(`/api/v1/events/${eventId}`, { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["events"] }),
  });
}

export function useGraphMermaid() {
  return useQuery({
    queryKey: ["graph", "mermaid"],
    queryFn: () => apiFetch<{ mermaid: string }>("/api/v1/graph/mermaid"),
    staleTime: Infinity, // static topology, never changes at runtime
  });
}
