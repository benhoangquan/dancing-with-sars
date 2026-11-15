import { App } from "@/components/App";
import { loadChapters } from "@/lib/chapters";

export default function Home() {
  return <App chapters={loadChapters()} />;
}
