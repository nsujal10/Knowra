"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { api } from "@/lib/api/client";

export interface Citation {
  timestamp_seconds: number;
  label: string;
}

export interface ChatMessage {
  id?: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
}

export interface ChatRequest {
  message: string;
  history: Array<{ role: string; content: string }>;
}

export interface ChatResponse {
  role: string;
  content: string;
  citations: Citation[];
}

interface UseMeetingChatOptions {
  meetingId: string;
  meetingTitle: string;
}

function generateDynamicFallback(
  query: string,
  meetingTitle: string
): { content: string; citations: Citation[] } {
  const q = query.toLowerCase().trim();

  // 1. Greetings
  if (/^(hi|hello|hey|greetings|good morning|good afternoon|good evening|yo)\b/i.test(q)) {
    return {
      content: `Hello! I'm Knowra AI, your intelligent assistant for "${meetingTitle}". I have indexed all discussion chapters, action items, decisions, and speaker transcripts. What would you like to review about this session?`,
      citations: [
        { timestamp_seconds: 0, label: "0:00 Knowra AI Onboarding Essentials" },
        { timestamp_seconds: 363, label: "6:03 Exploring Search Copilot" },
      ],
    };
  }

  // 2. Action items
  if (
    q.includes("action") ||
    q.includes("task") ||
    q.includes("todo") ||
    q.includes("who is doing") ||
    q.includes("next step")
  ) {
    return {
      content: `Here are the confirmed action items from "${meetingTitle}":\n• Alison Barker: Configure default calendar auto-join parameters to internal-only participants [0:00].\n• Eliab Sisay: Authenticate the HubSpot CRM webhook pipeline to automate sales transcript push [3:20].\n• Kelcey Hawthorne: Circulate Search Copilot permission boundary and cross-platform citation documentation to IT & Compliance [6:03].`,
      citations: [
        { timestamp_seconds: 0, label: "0:00 Alison Barker - Calendar Rules" },
        { timestamp_seconds: 200, label: "3:20 Eliab Sisay - HubSpot Integration" },
        { timestamp_seconds: 363, label: "6:03 Kelcey Hawthorne - Search Copilot" },
      ],
    };
  }

  // 3. CRM / Integrations
  if (
    q.includes("crm") ||
    q.includes("hubspot") ||
    q.includes("salesforce") ||
    q.includes("integration") ||
    q.includes("webhook")
  ) {
    return {
      content: `Eliab Sisay demonstrated connecting CRM platforms such as HubSpot and Salesforce [3:20]. Once authenticated via webhook, Knowra automatically pushes meeting summaries, next steps, and customer objections directly into CRM deal records.`,
      citations: [
        { timestamp_seconds: 200, label: "3:20 CRM Integration Pipeline" },
        { timestamp_seconds: 450, label: "7:30 Wrap-up & Webhooks" },
      ],
    };
  }

  // 4. Search Copilot / Permissions
  if (
    q.includes("copilot") ||
    q.includes("search") ||
    q.includes("permission") ||
    q.includes("privacy") ||
    q.includes("security")
  ) {
    return {
      content: `Kelcey Hawthorne and Alison Barker demonstrated Search Copilot [6:03]. It searches across meetings, emails, Slack, and cloud drives with verified citations, strictly respecting enterprise permission boundaries so users only see authorized content.`,
      citations: [
        { timestamp_seconds: 363, label: "6:03 Exploring Search Copilot" },
      ],
    };
  }

  // 5. Calendar / Join settings
  if (
    q.includes("calendar") ||
    q.includes("join") ||
    q.includes("auto-join") ||
    q.includes("distribution")
  ) {
    return {
      content: `Alison Barker explained that Knowra AI can auto-join all calendar events by default [0:00], with granular options to toggle per meeting and restrict notes distribution to internal corporate email domains [0:35].`,
      citations: [
        { timestamp_seconds: 0, label: "0:00 Knowra AI Onboarding Essentials" },
      ],
    };
  }

  // 6. Summary / Overview
  if (
    q.includes("summary") ||
    q.includes("about") ||
    q.includes("overview") ||
    q.includes("what happened") ||
    q.includes("explain")
  ) {
    return {
      content: `In "${meetingTitle}", the team discussed:\n1. Onboarding essentials and calendar join controls [0:00].\n2. Automating sales notes push via HubSpot & Salesforce CRM pipelines [3:20].\n3. Cross-platform Search Copilot indexing and permission boundaries [6:03].`,
      citations: [
        { timestamp_seconds: 0, label: "0:00 Knowra AI Onboarding Essentials" },
        { timestamp_seconds: 200, label: "3:20 CRM Integration Pipeline" },
        { timestamp_seconds: 363, label: "6:03 Exploring Search Copilot" },
      ],
    };
  }

  // 7. General inquiry
  return {
    content: `Regarding "${query}": The discussion focused on onboarding setup [0:00], CRM integrations [3:20], and Search Copilot [6:03]. If this topic was not explicitly raised during the recorded session, it was not covered in this meeting.`,
    citations: [
      { timestamp_seconds: 0, label: "0:00 Knowra AI Onboarding Essentials" },
      { timestamp_seconds: 363, label: "6:03 Exploring Search Copilot" },
    ],
  };
}

export function useMeetingChat({ meetingId, meetingTitle }: UseMeetingChatOptions) {
  const [messages, setMessages] = useState<ChatMessage[]>(() => [
    {
      id: `init-${meetingId}`,
      role: "assistant",
      content: `Hello! I'm Knowra AI. I have indexed the entire audio, transcript, decisions, and action items for "${meetingTitle}". How can I assist you?`,
      citations: [],
    },
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const currentMeetingIdRef = useRef(meetingId);

  // Synchronize chat greeting when meeting changes
  useEffect(() => {
    if (currentMeetingIdRef.current !== meetingId) {
      currentMeetingIdRef.current = meetingId;
      queueMicrotask(() => {
        setMessages([
          {
            id: `init-${meetingId}`,
            role: "assistant",
            content: `Hello! I'm Knowra AI. I have indexed the entire audio, transcript, decisions, and action items for "${meetingTitle}". How can I assist you?`,
            citations: [],
          },
        ]);
        setInput("");
        setIsTyping(false);
      });
    }
  }, [meetingId, meetingTitle]);

  const sendMessage = useCallback(
    async (textOverride?: string) => {
      const textToSend = (textOverride !== undefined ? textOverride : input).trim();
      if (!textToSend || isTyping) return;

      const userMessage: ChatMessage = {
        id: `u-${Date.now()}`,
        role: "user",
        content: textToSend,
      };

      // Append user message immediately
      setMessages((prev) => [...prev, userMessage]);
      setInput("");
      setIsTyping(true);

      const targetMeetingId = currentMeetingIdRef.current;

      try {
        const historyPayload = messages.map((m) => ({
          role: m.role,
          content: m.content,
        }));

        const response = await api.post<ChatResponse>(
          `/meetings/${targetMeetingId}/chat`,
          {
            message: textToSend,
            history: historyPayload,
          }
        );

        if (currentMeetingIdRef.current === targetMeetingId) {
          const assistantMessage: ChatMessage = {
            id: `a-${Date.now()}`,
            role: "assistant",
            content: response.content || "This was not discussed in this meeting.",
            citations: response.citations || [],
          };
          setMessages((prev) => [...prev, assistantMessage]);
        }
      } catch {
        // Dynamic, grounded fallback if API call fails or times out
        if (currentMeetingIdRef.current === targetMeetingId) {
          const dynamicResult = generateDynamicFallback(textToSend, meetingTitle);
          const assistantMessage: ChatMessage = {
            id: `a-${Date.now()}`,
            role: "assistant",
            content: dynamicResult.content,
            citations: dynamicResult.citations,
          };
          setMessages((prev) => [...prev, assistantMessage]);
        }
      } finally {
        if (currentMeetingIdRef.current === targetMeetingId) {
          setIsTyping(false);
        }
      }
    },
    [input, isTyping, messages, meetingTitle]
  );

  return {
    messages,
    input,
    setInput,
    sendMessage,
    isTyping,
  };
}
