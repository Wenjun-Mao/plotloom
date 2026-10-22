"use strict";

class DashboardJobList {
  constructor(body, select, format) {
    this.body = body;
    this.select = select;
    this.format = format;
    this.rows = new Map();
    this.order = "";
  }

  create(id) {
    const row = document.createElement("tr");
    const cells = ["任务 / 创建时间", "状态", "设置", "生成耗时", "输出"].map(
      (label) => {
        const cell = document.createElement("td");
        cell.dataset.label = label;
        row.append(cell);
        return cell;
      },
    );
    const identity = document.createElement("button");
    identity.type = "button";
    identity.textContent = id;
    identity.onclick = () => this.select(id);
    const created = document.createElement("small");
    cells[0].append(identity, created);
    const badge = document.createElement("span");
    cells[1].append(badge);
    const availability = document.createElement("span");
    const actions = document.createElement("div");
    actions.className = "job-actions";
    const open = document.createElement("button");
    open.type = "button";
    open.onclick = () => this.select(id);
    open.setAttribute("aria-controls", "detail-panel");
    const download = document.createElement("a");
    download.className = "button";
    download.textContent = "下载";
    download.setAttribute("aria-label", `下载 ${id} 的原始文件`);
    download.href = `/dashboard/media/${encodeURIComponent(id)}?download=true`;
    actions.append(open, download);
    cells[4].append(availability, actions);
    return { row, cells, identity, created, badge, availability, open, download };
  }

  render(jobs, selected) {
    const next = new Map();
    for (const job of jobs) {
      const entry = this.rows.get(job.id) || this.create(job.id);
      const value = this.format(job);
      entry.created.textContent = value.created;
      entry.identity.setAttribute("aria-controls", "detail-panel");
      entry.badge.textContent = value.status;
      entry.badge.className = "badge" +
        (job.status === "succeeded" ? " good" :
          ["failed", "outcome_unknown"].includes(job.status) ? " bad" : "");
      entry.cells[2].textContent = value.settings;
      entry.cells[3].textContent = value.elapsed;
      const available = job.output === "available";
      entry.availability.hidden = available;
      entry.availability.textContent = value.output;
      entry.open.textContent = available ? "预览" : "详情";
      entry.open.setAttribute("aria-label", `${available ? "预览" : "查看详情"} ${job.id}`);
      entry.download.hidden = !available;
      next.set(job.id, entry);
    }
    const order = jobs.map((job) => job.id).join(",");
    // Polling updates existing controls in place, preserving keyboard focus.
    if (order !== this.order) {
      this.body.replaceChildren(...Array.from(next.values(), (entry) => entry.row));
      this.order = order;
    }
    this.rows = next;
    this.highlight(selected);
  }

  highlight(id) {
    for (const [key, entry] of this.rows) {
      entry.identity.classList.toggle("selected", key === id);
      entry.cells[0].classList.toggle("current", key === id);
    }
  }

  returnTo(id) {
    const target = this.rows.get(id)?.identity || document.getElementById("jobs-title");
    target.scrollIntoView({ block: "center" });
    target.focus({ preventScroll: true });
  }
}
