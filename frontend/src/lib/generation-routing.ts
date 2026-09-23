/** Keep a PR generation separate from automatic Space updates. */
export function resolveGenerationRouting(
  overrideRepoId: string | undefined,
  currentRepoId: string | null,
  shouldCreatePR: boolean | undefined,
  pendingPRRepoId: string | null
): { existingRepoId: string | undefined; skipAutoDeploy: boolean } {
  const skipAutoDeploy = Boolean(shouldCreatePR || pendingPRRepoId);

  return {
    existingRepoId: skipAutoDeploy ? undefined : (overrideRepoId || currentRepoId || undefined),
    skipAutoDeploy,
  };
}
