export interface WorkspaceFolder {
  id: string;
  name: string;
  description: string;
  color: string;
  bgGradient: string;
  borderClass: string;
  tagColor: string;
  category: "ENGINEERING" | "EXECUTIVE" | "PRODUCT" | "SALES" | "OPERATIONS";
  visibility: "WORKSPACE" | "TEAM" | "PRIVATE";
  meetingCount: number;
  decisionsCount: number;
  actionsCount: number;
  updatedAt: string;
  members: Array<{
    name: string;
    initials: string;
    avatarBg: string;
  }>;
  autoRouteTags: string[];
  recentMeetings: Array<{
    id: string;
    title: string;
    date: string;
    duration: string;
    status: "COMPLETED" | "PROCESSING" | "RECORDING";
  }>;
}

// Clean initial folders: No hardcoded mock/seed folders.
// The user starts clean and manages only their own collections.
export const DEFAULT_WORKSPACE_FOLDERS: WorkspaceFolder[] = [];
