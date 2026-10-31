# Branching-game production playbook

Use these three practices when taking an authored branching story through Plotloom to a standalone game.

## 1. Map the routes before making footage

For each decision, write the exact label the player sees, where it leads, and what changes because they chose it. Trace every path from the opening to its ending. Use that same map when checking the exported game.

In *The Last Projection*, sealing the evidence immediately ends with Xu Wei handing it over alone. Hearing A-Lan out gives the player a second choice between submitting the evidence together and destroying it. The short route needs one decision and the other two need two. Keeping that asymmetry preserves the consequence of acting immediately. [Authored route map](../roadmap/2026-10-30-first-h5-story.md#complete-route-graph)

## 2. State what stays true until the player chooses

At a branch, write down who holds what, which action has already happened, and which action belongs only to the next scene. Compare that direction with the actual image tool arguments and the complete video request, including instructions Plotloom adds.

In the opening, A-Lan still has her hand on Xu Wei’s. Only on the “hear her out” route does Xu Wei put the card down and A-Lan let go. One image request moved those actions into the opening. The team retained the candidate unselected and corrected the direction. A separate video request required a continuous shot even though the author allowed a cut to card fragments. That contradiction came from Plotloom’s own instructions, so the fix belonged there. [Image request finding](../roadmap/2026-10-30-last-projection-h5-mvp.md#plan-review-and-production-learning) · [Video request finding](../verification/2026-10-31-authored-shot-structure.md)

## 3. Play the package the player receives

Early in production, use retained media in a small complete fixture to exercise an opening, a choice, an ending, and restart. At delivery, download the game from the installed app, unpack it outside the checkout, and play it with Plotloom unavailable. Follow every route from the map. Check the dialogue, choice labels, ending cards, replay, and resume after reload.

For *The Last Projection*, the installed download matched the delivery ZIP byte for byte. All three routes played in Chromium and WebKit over static HTTP. Opening the local file in Safari covered the short route. Record playback coverage separately from any judgment about acting, visuals, or sound. Those creative qualities remained unreviewed in this run. [Executed playback checks](../verification/2026-10-31-last-projection-functional-closeout.md#executed-functional-coverage)
