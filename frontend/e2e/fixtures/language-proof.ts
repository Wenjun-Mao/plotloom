import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

export type FixtureProofEnvironment = { apiOrigin: string; outputsRoot: string; applicationDataRoot: string };
type Stage = "outline" | "branches" | "characters" | "art" | "script" | "storyboard-review";
const environments = new Map<string, FixtureProofEnvironment>();
const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
const adapter = path.join(repositoryRoot, "frontend/e2e/fixtures/f5a/synthetic_language_check.py");

export function registerFixtureProofEnvironment(projectId: string, environment: FixtureProofEnvironment): void {
  environments.set(projectId, environment);
}

export function fixtureProofEnvironment(projectId: string): FixtureProofEnvironment {
  const environment = environments.get(projectId);
  if (!environment) throw new Error(`Missing explicit language-proof environment for ${projectId}`);
  return environment;
}

/** Distinct completed synthetic evidence for exact bytes; never native dispatch. */
export async function installSyntheticLanguageProof(environment: FixtureProofEnvironment, projectId: string,
  stage: Stage, candidateJobId: string, allowTerminalDelivery = false, candidate?: Record<string, unknown>): Promise<void> {
  const args = ["run", "--locked", "--no-sync", "python", adapter,
    "--outputs-root", environment.outputsRoot, "--application-data-root", environment.applicationDataRoot,
    "--project-id", projectId, "--candidate-job-id", candidateJobId, "--stage", stage];
  if (candidate) args.push("--candidate-json", JSON.stringify(candidate));
  const output = execFileSync("uv", args, { cwd: repositoryRoot, encoding: "utf8" });
  const proof = JSON.parse(output) as Record<string, unknown>;
  if (allowTerminalDelivery && proof.candidateJobId === candidateJobId
      && proof.proofKind === "synthetic-test-skip" && proof.dispatchPerformed === false
      && proof.reason === "terminal-or-replaced") return;
  if (proof.candidateJobId !== candidateJobId || proof.proofKind !== "synthetic-test-receipt"
      || proof.dispatchPerformed !== false || proof.verdict !== "pass"
      || typeof proof.candidateHash !== "string" || typeof proof.bindingHash !== "string"
      || typeof proof.receiptHash !== "string") {
    throw new Error(`Synthetic language proof did not bind the current candidate: ${output}`);
  }
}

export async function installDeliveredLanguageProof(request: { projectId: string; stage: Stage }, jobId: string): Promise<void> {
  await installSyntheticLanguageProof(fixtureProofEnvironment(request.projectId), request.projectId,
    request.stage, jobId, true);
}
