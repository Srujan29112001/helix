import type { Metadata } from "next";
import { StudioClient } from "@/components/studio/studio-client";

export const metadata: Metadata = {
  title: "Studio",
  description:
    "Upload a dataset, set a goal, and watch Helix's nine agents plan, code, execute, self-correct, model, explain, visualize, research and report — live.",
};

export default function StudioPage() {
  return <StudioClient />;
}
