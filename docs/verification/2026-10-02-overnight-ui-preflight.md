# Overnight creator UI preflight

Run on the exact browser, host and served revision intended for unattended work.
Use a labelled disposable fixture, with generation disabled for the preflight.

1. Verify the host is accessible and the intended workspace loads. A navigable
   DOM alone does not establish usable mutation or confirmation access.
2. Open a domain confirmation, inspect its target and consequence, cancel it and
   verify no mutation. Reopen, Escape, and verify focus returns to the trigger.
3. Reopen and reload or change target/revision; verify consent is invalidated and
   no action is replayed. Confirm a disposable action once; verify its exact
   result and no duplicate write. Exercise keyboard focus containment.
4. Verify application errors/stale responses leave usable recovery controls and
   require a fresh explicit decision. Do not bypass browser security or native
   safety denials. Record failures and stop affected operations.
5. Establish who can actually hear and review original/final audio. Audio codec,
   ffprobe duration, waveform, or a successfully pressed Play button are not
   audition evidence. If sound is inaccessible, retain candidates unselected and
   arrange owner review; never convert operational confirmation into creative
   audio approval.
6. Record generation/handoff deadlines, remaining unknown dispatches and the
   supported completion-reporting route before leaving work unattended.

ADR 0101 owns creator confirmation semantics. These checks do not grant new
provider authority, deletion authority, creative acceptance or deadline extension.
