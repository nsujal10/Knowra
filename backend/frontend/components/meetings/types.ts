export interface Metric {
  score: number;
  label: string;
  trend: number[];
  status: 'GOOD' | 'NEUTRAL' | 'WARNING' | 'CRITICAL';
}

export interface ActionItem {
  id: string;
  owner: string;
  text: string;
  timestampSeconds: number;
}

export interface DiscussionPoint {
  id: string;
  title: string;
  summary: string;
  timestampSeconds: number;
}

export interface Chapter {
  id: string;
  title: string;
  timestampSeconds: number;
  thumbnail?: string;
  durationStr: string;
}

export interface MeetingIntelligence {
  title: string;
  date: string;
  timeRange: string;
  source: 'Zoom' | 'Teams' | 'Google Meet' | 'Upload';
  participants: string[];
  metrics: {
    report: Metric;
    engagement: Metric;
    sentiment: Metric;
  };
  summary: string;
  actionItems: ActionItem[];
  discussionPoints: DiscussionPoint[];
  chapters: Chapter[];
}
