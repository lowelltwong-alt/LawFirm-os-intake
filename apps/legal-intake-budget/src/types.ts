export type GateState = "passed" | "blocked" | "pending" | "failed";

export type ArtifactStatus = "present" | "missing" | "blocked" | "pending_review";

export type ReviewArtifact = {
  artifactId: string;
  label: string;
  fileName: string;
  status: ArtifactStatus;
  owner: string;
  gateState: GateState;
  candidateOnly: boolean;
  externalWritesPerformed: boolean;
  notes: string[];
};

export type BoundaryFlags = {
  readOnly: boolean;
  localJsonOnly: boolean;
  networkCallsAllowed: boolean;
  mutationCommandsAllowed: boolean;
  exceptionLakeWritesAllowed: boolean;
  sqliteWritesAllowed: boolean;
  publicRuntimeIngestionAllowed: boolean;
  budgetSubmissionAllowed: boolean;
  matterOpeningAllowed: boolean;
};

export type ReviewManifest = {
  manifestId: string;
  generatedAt: string;
  runLabel: string;
  practiceArea: string;
  matterFamily: string;
  overallStatus: GateState;
  boundaryFlags: BoundaryFlags;
  artifacts: ReviewArtifact[];
  blockerSummary: string[];
  redTeamNotes: string[];
};
