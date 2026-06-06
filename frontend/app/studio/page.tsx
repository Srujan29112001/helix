import type { Metadata } from "next";
import { StudioClient } from "@/components/studio/studio-client";

export const metadata: Metadata = {
  title: "Studio",
  description:
    "Upload a dataset, set a goal, and watch Helix's seven agents plan, code, execute, self-correct, model, explain and report — live.",
};

export default function StudioPage() {
  return <StudioClient />;
}
