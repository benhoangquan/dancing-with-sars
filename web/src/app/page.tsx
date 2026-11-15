import { StoryViewport } from "@/components/story/StoryViewport";
import { loadChapters } from "@/lib/chapters";

export default function Home() {
  return <StoryViewport chapters={loadChapters()} />;
}
