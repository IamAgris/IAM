import { IAMInterface } from "@/components/iam/interface";

// IAM has exactly one page. Conversation deep-links use ?conversation=<id> so
// no second route is needed. Reading searchParams opts this page into dynamic
// rendering; force-dynamic keeps behaviour explicit across Next.js versions.
export const dynamic = "force-dynamic";

export default async function Home({
  searchParams,
}: {
  searchParams: Promise<{ conversation?: string | string[] }>;
}) {
  const params = await searchParams;
  const raw = params.conversation;
  const initialConversationId = Array.isArray(raw) ? raw[0] : raw;
  return <IAMInterface initialConversationId={initialConversationId} />;
}
