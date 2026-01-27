// Centralized query key factories for type-safe, consistent cache keys
// This file consolidates all query keys from across the codebase

export const threadKeys = {
  all: ['threads'] as const,
  lists: () => [...threadKeys.all, 'list'] as const,
  paginated: (page: number, limit: number) => 
    [...threadKeys.lists(), 'paginated', { page, limit }] as const,
  byProject: (projectId: string) => 
    [...threadKeys.lists(), 'project', projectId] as const,
  details: (threadId: string) => 
    [...threadKeys.all, 'detail', threadId] as const,
  messages: (threadId: string) => 
    [...threadKeys.details(threadId), 'messages'] as const,
  agentRuns: (threadId: string) => 
    [...threadKeys.details(threadId), 'agent-runs'] as const,
};

export const projectKeys = {
  all: ['projects'] as const,
  lists: () => [...projectKeys.all, 'list'] as const,
  details: (projectId: string) => 
    [...projectKeys.all, 'detail', projectId] as const,
  public: () => [...projectKeys.all, 'public'] as const,
  threads: (projectId: string) =>
    [...projectKeys.details(projectId), 'threads'] as const,
};

export const accountKeys = {
  all: ['accounts'] as const,
  lists: () => [...accountKeys.all, 'list'] as const,
  current: () => [...accountKeys.all, 'current'] as const,
};

export const agentKeys = {
  all: ['agents'] as const,
  lists: () => [...agentKeys.all, 'list'] as const,
  details: (agentId: string) => 
    [...agentKeys.all, 'detail', agentId] as const,
  byProject: (projectId: string) => 
    [...agentKeys.lists(), 'project', projectId] as const,
};

export const systemKeys = {
  status: ['system-status'] as const,
  health: ['api-health'] as const,
  healthV2: ['api-health', 'v2'] as const,
};

export const userKeys = {
  profile: ['user', 'profile'] as const,
  settings: ['user', 'settings'] as const,
  adminRole: ['user', 'admin-role'] as const,
};

export const billingKeys = {
  all: ['billing'] as const,
  subscription: () => [...billingKeys.all, 'subscription'] as const,
  usage: () => [...billingKeys.all, 'usage'] as const,
};
