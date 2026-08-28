import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";

/** Shared shape for the 5 config resources -- list/create/update/status-toggle
 * all follow the same REST pattern (see app/api/*.py), so this factory avoids
 * repeating the same react-query boilerplate 5 times. */
export function createResourceHooks<TRead, TCreate, TUpdate>(
  basePath: string,
  resourceKey: string,
) {
  function useList(params?: Record<string, string>) {
    const qs = params ? `?${new URLSearchParams(params).toString()}` : "";
    return useQuery({
      queryKey: [resourceKey, "list", params ?? {}],
      queryFn: () => apiFetch<TRead[]>(`${basePath}${qs}`),
    });
  }

  function useCreate() {
    const queryClient = useQueryClient();
    return useMutation({
      mutationFn: (body: TCreate) => apiFetch<TRead>(basePath, { method: "POST", body }),
      onSuccess: () => queryClient.invalidateQueries({ queryKey: [resourceKey] }),
    });
  }

  function useUpdate() {
    const queryClient = useQueryClient();
    return useMutation({
      mutationFn: ({ id, body }: { id: string; body: TUpdate }) =>
        apiFetch<TRead>(`${basePath}/${id}`, { method: "PATCH", body }),
      onSuccess: () => queryClient.invalidateQueries({ queryKey: [resourceKey] }),
    });
  }

  function useAction(action: string) {
    const queryClient = useQueryClient();
    return useMutation({
      mutationFn: (id: string) => apiFetch<TRead>(`${basePath}/${id}/${action}`, { method: "POST" }),
      onSuccess: () => queryClient.invalidateQueries({ queryKey: [resourceKey] }),
    });
  }

  return { useList, useCreate, useUpdate, useAction };
}
