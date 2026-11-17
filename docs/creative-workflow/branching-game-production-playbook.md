# Branching-game production playbook

Use these practices when taking an authored branching story through Plotloom to a standalone game.

## 1. Map the routes before making footage

For each decision, write the exact label the player sees, where it leads, and what changes because they chose it. Trace every path from the opening to its ending. Use that same map when checking the exported game.

In *The Last Projection*, sealing the evidence immediately ends with Xu Wei handing it over alone. Hearing A-Lan out gives the player a second choice between submitting the evidence together and destroying it. The short route needs one decision and the other two need two. Keeping that asymmetry preserves the consequence of acting immediately. [Authored route map](../../.local/stories/放映室最后一夜/2026-10-30-first-h5-story.md#complete-route-graph)

## 2. State what stays true until the player chooses

At a branch, write down who holds what, which action has already happened, and which action belongs only to the next scene. Compare that direction with the actual image tool arguments and the complete video request, including instructions Plotloom adds.

In the opening, A-Lan still has her hand on Xu Wei’s. Only on the “hear her out” route does Xu Wei put the card down and A-Lan let go. One image request moved those actions into the opening. The team retained the candidate unselected and corrected the direction. A separate video request required a continuous shot even though the author allowed a cut to card fragments. That contradiction came from Plotloom’s own instructions, so the fix belonged there. [Image request finding](../roadmap/2026-10-30-last-projection-h5-mvp.md#plan-review-and-production-learning) · [Video request finding](../verification/2026-10-31-authored-shot-structure.md)

## 3. Keep dialogue out of the generated picture

Use Quality 8 for final H3 clips. Give H3 the exact authored words as speech and place intentional writing, such as a sign, on its specified object. The standalone player displays captions and choice labels. Once the clip is technically usable, continue production. [Final H3 directions skill](../../.agents/skills/plotloom-video-directions-specialist/SKILL.md)

## 4. Let the film run until the player needs to decide or read

When a scene has one predetermined next step, play the clip through its natural end and go straight to that step. In *The Last Projection* V3, choosing to watch the surveillance recording has already settled what happens next. When **先看那一晚** ends, cut directly to A-Lan’s response.

At a decision, hold the preceding clip’s final frame and show the untimed choices inside the picture. The first choice should leave the card and both women visible. On a text-only passage, let the player read at their own pace and show one **进入下一幕** button. At the end of a route, show the ending card.

Keep pause and replay with the video controls. Put deliberate returns to earlier decisions in the route journal (V3’s **交接簿**). During playtesting, watch a scene transition without touching the controls, wait on a reading passage, then try each choice at desktop and phone widths. Revisit a decision through the journal and reload there to check that its held frame belongs to the route actually played. [Standalone player contract](../adr/0227-standalone-player-export.md)

## 5. Carry the player’s sound settings across clips

Start the exported game, turn sound on with the native video control and set a recognizable volume, such as 35%. Let a clip end, choose a branch, then reload and continue. The next clip should still be audible at that volume, and the game’s sound button should agree with the native control. Repeat with the game’s mute button and verify that an intentional mute persists too. If the browser blocks playback, let the player press Play with their sound preference intact. [Sound and choice playback checks](../roadmap/2026-10-30-last-projection-h5-mvp.md#current-status)

## 6. Play the package the player receives

Early in production, use retained media in a small complete fixture to exercise an opening, a choice, an ending, and restart. At delivery, download the game from the installed app, unpack it outside the checkout, and play it with Plotloom unavailable. Follow every route from the map. Check the dialogue, choice labels, ending cards, replay, and resume after reload.

For *The Last Projection*, the installed download matched the delivery ZIP byte for byte. All three routes played in Chromium and WebKit over static HTTP. Opening the local file in Safari covered the short route. Record playback coverage separately from any judgment about acting, visuals, or sound. Those creative qualities remained unreviewed in this run. [Executed playback checks](../verification/2026-10-31-last-projection-functional-closeout.md#executed-functional-coverage)

### V3 recap, reading pause and chapter progress

A short route recap immediately before a decision belongs with that held-frame
decision: keep its route-owned words available through an optional disclosure,
with choices usable immediately. Do not add a recap advance button or timer.
A substantive reading passage with new story material remains a deliberate
reading pause, displaying the preceding route film frame and one advance action.
Chapter progress follows the displayed narrative node, independently of recap
copy. Preserve graph, route/archive/knowledge identities and current-position
Continue, including saves located at a pre-choice recap.
