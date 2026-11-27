"use client";

import { IAMInterface } from "@/components/iam/interface";

interface ConversationPageProps {
  params: { id: string };
}

export default function ConversationPage({ params }: ConversationPageProps) {
  return <IAMInterface initialConversationId={params.id} />;
}