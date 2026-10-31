# 《放映室最后一夜》 / The Last Projection

## Working draft

Written 2026-10-30 by the user-requested GPT-6.1 Terra / Max subagent, with root
checking route completeness and assembly practicality. This is the first H5
prototype's working story, not a polished final screenplay. Chinese is the
drafting default; the English synopsis supports discussion. No Plotloom project,
canonical story installation or media generation has been created from it yet.
The [MVP boundary](2026-10-30-first-real-game-benchmarks.md) remains controlling:
standalone browser delivery, lightly styled game UI, no audiovisual quality
inspection during the first build, and source-to-asset bindings for later updates.

## Concept

半年前，旧电影院发生了一场小火。许微被认定负有责任，丢掉了放映员的岗位。
电影院明早交接，新发现的一张监控卡却证明，真正碰倒电暖器的是她的老同事
阿岚——而阿岚一直知道。

**English synopsis:** On the final night before an old cinema changes hands,
an archivist finds evidence that could clear her name in a fire investigation.
The evidence also implicates her oldest colleague, who hid the truth. The player
decides how to close the record and what their friendship can bear.

玩家扮演许微，目标是在旧馆档案交接前处理这份证据。交出证据并附上更正说明，
会让接手方看到真实经过；销毁它，则会让旧记录继续随档案交接。

## Characters and location

- **许微（Xu Wei）**：原放映员，半年前被调去整理档案；玩家角色。
- **阿岚（A-Lan）**：许微认识八年的同事，负责与她一起完成旧馆交接。
- **场景**：夜间的旧电影院放映室。工作台、工作灯、交接袋、读卡器和电暖器。
  监控回放使用同一房间的固定机位，剧情不需要呈现火灾。

Draft estimate: approximately 1–2 minutes per route, depending on scene length
and reading time; this is not a measured playback duration or production quota.
The short route has one decision; the two longer routes have two. No padding is
needed to reach the earlier tentative 3–5 minute suggestion.

## Complete route graph

```text
N00 发现监控卡
  │
 C01
  ├─ 现在写明真相并封存 ──────────→ E01 独自交接
  └─ 先听阿岚解释 → N10 对话
                       │
                      C02
                       ├─ 让她签字，一起交接 → E02 共同交接
                       └─ 销毁卡，保留旧记录 → E03 留下旧记录
```

Draft node/edge IDs are explicit authoring references for later mapping, not
new runtime contracts. There are no hidden flags, conditions, loops or joins.

| Edge ID | From | Exact choice label, or continuation | To |
|---|---|---|---|
| `edge_opening_choice` | N00 | Continuation | C01 |
| `edge_submit_alone` | C01 | 现在写明真相并封存 | E01 |
| `edge_hear_explanation` | C01 | 先听阿岚解释 | N10 |
| `edge_explanation_choice` | N10 | Continuation | C02 |
| `edge_submit_together` | C02 | 让她签字，一起交接 | E02 |
| `edge_destroy_evidence` | C02 | 销毁卡，保留旧记录 | E03 |

## Node script

### N00 — 发现

**画面与动作**

夜晚，放映室只亮着工作灯。许微整理交接袋，从读卡器里取出一张存储卡。
阿岚看见后伸手按住她的手。

短暂插入监控画面：固定机位拍到阿岚碰倒电暖器。许微当时不在房间。
画面无需表现火焰；这一信息同时由字幕明确说明。

**对白**

- 阿岚：“别放了。半年前那场火，是我碰倒了电暖器。”
- 许微：“报告上写的是我违规操作。你一直知道？”
- 阿岚：“我把监控卡藏起来了。我怕他们追究我。”
- 许微：“这半年，我被调来整理档案，大家都以为是我。”
- 阿岚：“明早新馆主就来接收了。你把卡和更正说明放进交接袋，他们就会知道真相。”
- 许微：“你的名字也会留在记录里。”
- 阿岚：“我知道。你能先听我解释吗？”

进入 C01。

### C01 — 第一次选择

交接袋、存储卡和两人留在画面中，等待玩家选择。没有倒计时。

- **现在写明真相并封存** → E01
- **先听阿岚解释** → N10

### N10 — 解释

**画面与动作**

许微把卡留在桌上。阿岚松开手，站到桌子另一侧。

**对白**

- 阿岚：“那晚我踢倒了电暖器，以为火已经灭了。后来他们说是你的机器出了问题。”
- 许微：“你看着我被调岗，什么都没说。”
- 阿岚：“是。我把卡藏了半年。每次想说，都怕自己要承担后果。”
- 许微：“我连再碰一次放映机都不敢。”
- 阿岚：“如果你决定交出去，我会亲手在说明上签名。你不用原谅我。”

进入 C02。

### C02 — 第二次选择

- **让她签字，一起交接** → E02
- **销毁卡，保留旧记录** → E03

### E01 — 独自交接

**画面与动作**

许微写下更正说明，将存储卡放进交接袋并封好。阿岚看着她，拿起外套，
独自走出放映室。许微留在工作灯下。

**对白**

- 许微：“我等了半年。今天我要自己把它写下来。”
- 阿岚：“我会承担。但你连让我说完的机会都没有。”

**结束卡**

> **独自交接**
>
> 证据和更正说明随档案交出。
>
> 许微为自己留下了证明，阿岚独自离开了放映室。

按钮：**重新开始**。

### E02 — 共同交接

**画面与动作**

阿岚在说明上签名，将笔递给许微。许微看了她一眼，也签下名字。
两人一起将存储卡放进交接袋，封口。

**对白**

- 阿岚：“这次，我会把我的名字写上去。”
- 许微：“先把真相留下。其他的事，以后再说。”

**结束卡**

> **共同交接**
>
> 两人的说明和监控卡随档案交出。
>
> 真相有了记录，她们也给彼此留下了继续说话的空间。

按钮：**重新开始**。

### E03 — 留下旧记录

**画面与动作**

许微拿起剪刀，剪断存储卡，将碎片放进废料袋。
她封好没有更正说明的交接袋。阿岚没有伸手阻止。

**对白**

- 阿岚：“你真的决定让旧记录留下？”
- 许微：“我知道别人还是会误会。我不想再把这一晚交给那场火。”
- 阿岚：“我欠你的，不会因为这张卡消失。”

**结束卡**

> **留下旧记录**
>
> 旧档案按原样交接，许微失去了最直接的证据。
>
> 她选择私下结束这件事，也留下了那份误解。

按钮：**重新开始**。

## First playable slice and assembly notes

First slice: **N00 → C01 → E01 → Restart**. It includes an opening, an actual
choice, a consequence and an ending card. Add N10/C02/E02/E03 to complete the
other two routes. The full MVP needs all three routes; the slice is the early
assembly checkpoint.

Media-bearing draft nodes are N00, N10, E01, E02 and E03. Choice nodes can hold
the preceding image/frame and use real HTML controls. N00 may have a separate
surveillance insert. This is an inventory for planning, not a fixed job count.

Minimum inventory: two character identities; one projection-room location;
work light, memory card, reader, handover envelope, paper/pen, scissors, scrap
bag, heater; and a short surveillance image/clip in the same location. Dialogue,
choice labels, title and ending cards are author-controlled UI text. Paper and
equipment require no generated readable lettering or exact lip synchronization.
The surveillance insert is supporting evidence; the dialogue also supplies the
necessary fact. Card destruction can be represented by a cut to fragments plus
text, without depending on a continuous close-up of precise cutting motion.

Use a dark background, warm work-light accent, a simple film-strip edge and
legible choice panels. Ending cards can resemble plain handover records with a
little framing. This lightweight treatment meets the MVP intention; elaborate
animation, custom illustration or final visual polish is unnecessary.

Reserve logical slots tied to these draft node roles, then map them to actual
Plotloom sources and selected media during production. Regeneration must not
require rewriting the choice graph, ending text or UI styling. Detailed timing,
shots and actual source IDs belong to the production plan and Plotloom project.

## Bounded draft check

All seven nodes are reachable from N00. The six edges yield exactly three
complete routes: N00/C01/E01; N00/C01/N10/C02/E02; N00/C01/N10/C02/E03.
Each choice has a visible consequence for the evidence/record or the relationship;
every ending resolves that night's handover. No unseen character, exact generated
text, live service, hidden state or sequel is required to understand the outcome.

Root accepted this as a viable working draft without another writing round.
This is a route/buildability judgment, not a claim of owner creative review,
produced media quality or a finished game. No quality evaluator, generation,
software test run, publication or CI was invoked for this draft.
