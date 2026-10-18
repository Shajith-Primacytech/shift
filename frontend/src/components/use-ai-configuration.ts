"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AIConfiguration } from "@/lib/ai-models";

export function useAIConfiguration() {
  const [configuration, setConfiguration] = useState<AIConfiguration>();
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let active = true;
    void api<AIConfiguration>("/ai/configuration")
      .then((value) => {
        if (active) setConfiguration(value);
      })
      .catch(() => {})
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);
  return { configuration, loading };
}
