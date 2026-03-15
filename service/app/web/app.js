const state = {
  searchEnvelope: null,
  detailEnvelope: null,
  currentJson: null,
};

const elements = {
  baseUrl: document.getElementById("base-url"),
  sharedCookie: document.getElementById("shared-cookie"),
  rememberCookie: document.getElementById("remember-cookie"),
  clearSession: document.getElementById("clear-session"),
  refreshHealth: document.getElementById("refresh-health"),
  serviceStatus: document.getElementById("service-status"),
  serviceLatency: document.getElementById("service-latency"),
  metricSearchCount: document.getElementById("metric-search-count"),
  metricDetailState: document.getElementById("metric-detail-state"),
  metricRequestId: document.getElementById("metric-request-id"),
  searchForm: document.getElementById("search-form"),
  searchSubmit: document.getElementById("search-submit"),
  fillSearchDemo: document.getElementById("fill-search-demo"),
  detailForm: document.getElementById("detail-form"),
  detailSubmit: document.getElementById("detail-submit"),
  fillDetailDemo: document.getElementById("fill-detail-demo"),
  searchResults: document.getElementById("search-results"),
  detailResult: document.getElementById("detail-result"),
  searchResultSummary: document.getElementById("search-result-summary"),
  detailResultSummary: document.getElementById("detail-result-summary"),
  responseState: document.getElementById("response-state"),
  responseBanner: document.getElementById("response-banner"),
  jsonOutput: document.getElementById("json-output"),
  copyJson: document.getElementById("copy-json"),
  detailUrl: document.getElementById("detail-url"),
};

const SEARCH_DEMO = {
  keyword: "原创ip",
  note_type: "image",
  publish_time: "7d",
  sort_by: "most_liked",
  page_count: 1,
};

const DETAIL_DEMO_URL =
  "https://www.xiaohongshu.com/explore/69b5057b000000002302633c?xsec_source=pc_search&xsec_token=AB6Bzr6CEIrVFvWalQDxmuv99DXIQchT1cIE8jPi24MD8%3D";

const STORAGE_KEYS = {
  baseUrl: "redenote.baseUrl",
  rememberCookie: "redenote.rememberCookie",
  cookie: "redenote.cookie",
};

function init() {
  hydrateSession();
  bindEvents();
  refreshHealth();
}

function bindEvents() {
  elements.refreshHealth.addEventListener("click", refreshHealth);
  elements.searchForm.addEventListener("submit", handleSearchSubmit);
  elements.detailForm.addEventListener("submit", handleDetailSubmit);
  elements.fillSearchDemo.addEventListener("click", fillSearchDemo);
  elements.fillDetailDemo.addEventListener("click", fillDetailDemo);
  elements.copyJson.addEventListener("click", copyCurrentJson);
  elements.clearSession.addEventListener("click", clearSession);
  elements.baseUrl.addEventListener("change", persistSession);
  elements.rememberCookie.addEventListener("change", persistSession);
  elements.sharedCookie.addEventListener("input", persistSession);
}

function hydrateSession() {
  const defaultBaseUrl = window.location.origin && window.location.origin !== "null" ? window.location.origin : "http://127.0.0.1:8000";
  const storedBaseUrl = localStorage.getItem(STORAGE_KEYS.baseUrl);
  const storedRememberCookie = localStorage.getItem(STORAGE_KEYS.rememberCookie);
  const rememberCookie = storedRememberCookie === null ? true : storedRememberCookie === "1";
  const legacySessionCookie = sessionStorage.getItem(STORAGE_KEYS.cookie);
  const legacySessionRemember = sessionStorage.getItem(STORAGE_KEYS.rememberCookie);

  elements.baseUrl.value = storedBaseUrl || defaultBaseUrl;
  elements.rememberCookie.checked = rememberCookie;

  if (!localStorage.getItem(STORAGE_KEYS.cookie) && legacySessionCookie && legacySessionRemember === "1") {
    localStorage.setItem(STORAGE_KEYS.cookie, legacySessionCookie);
    localStorage.setItem(STORAGE_KEYS.rememberCookie, "1");
    sessionStorage.removeItem(STORAGE_KEYS.cookie);
    sessionStorage.removeItem(STORAGE_KEYS.rememberCookie);
  }

  if (rememberCookie) {
    elements.sharedCookie.value = localStorage.getItem(STORAGE_KEYS.cookie) || "";
  }
}

function persistSession() {
  localStorage.setItem(STORAGE_KEYS.baseUrl, normalizeBaseUrl(elements.baseUrl.value));
  localStorage.setItem(STORAGE_KEYS.rememberCookie, elements.rememberCookie.checked ? "1" : "0");

  if (elements.rememberCookie.checked) {
    localStorage.setItem(STORAGE_KEYS.cookie, elements.sharedCookie.value);
  } else {
    localStorage.removeItem(STORAGE_KEYS.cookie);
  }
}

function clearSession() {
  elements.sharedCookie.value = "";
  elements.rememberCookie.checked = false;
  localStorage.removeItem(STORAGE_KEYS.cookie);
  localStorage.setItem(STORAGE_KEYS.rememberCookie, "0");
  sessionStorage.removeItem(STORAGE_KEYS.cookie);
  sessionStorage.removeItem(STORAGE_KEYS.rememberCookie);
  persistSession();
  setBanner("已清空当前会话 Cookie。", "就绪", "success");
}

async function refreshHealth() {
  const startedAt = performance.now();
  setHealthStatus("服务状态检查中", "等待健康检查", "pending");

  try {
    const response = await fetch(`${getBaseUrl()}/healthz`, {
      headers: {
        Accept: "application/json",
      },
    });
    const payload = await response.json();
    if (!response.ok || !payload.success) {
      throw new Error(payload?.error?.message || `健康检查失败 (${response.status})`);
    }

    const latency = Math.round(performance.now() - startedAt);
    setHealthStatus("服务在线", `健康检查通过，耗时 ${latency} ms`, "success");
  } catch (error) {
    setHealthStatus("服务不可用", error.message || "无法连接服务", "error");
  }
}

async function handleSearchSubmit(event) {
  event.preventDefault();

  let cookie = "";
  try {
    cookie = getCookieOrThrow();
  } catch (error) {
    setBanner(error.message || "请先填写 Cookie。", "搜索未开始", "error");
    return;
  }

  const payload = {
    keyword: document.getElementById("search-keyword").value.trim(),
    note_type: document.getElementById("search-note-type").value,
    publish_time: document.getElementById("search-publish-time").value,
    sort_by: document.getElementById("search-sort-by").value,
    page_count: Number(document.getElementById("search-page-count").value || 1),
    cookie,
  };

  if (!payload.keyword) {
    setBanner("请先填写关键词。", "搜索未开始", "error");
    return;
  }

  await submitRequest({
    path: "/api/v1/rednote/search",
    payload,
    button: elements.searchSubmit,
    mode: "search",
  });
}

async function handleDetailSubmit(event) {
  event.preventDefault();

  let cookie = "";
  try {
    cookie = getCookieOrThrow();
  } catch (error) {
    setBanner(error.message || "请先填写 Cookie。", "详情未解析", "error");
    return;
  }

  const payload = {
    url: elements.detailUrl.value.trim(),
    cookie,
  };

  if (!payload.url) {
    setBanner("请先填写笔记链接。", "详情未解析", "error");
    return;
  }

  await submitRequest({
    path: "/api/v1/rednote/detail",
    payload,
    button: elements.detailSubmit,
    mode: "detail",
  });
}

async function submitRequest({ path, payload, button, mode }) {
  setButtonBusy(button, true);
  setBanner("请求进行中，请稍候。", mode === "search" ? "正在搜索" : "正在解析", "success");

  try {
    const startedAt = performance.now();
    const response = await fetch(`${getBaseUrl()}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(payload),
    });
    const envelope = await response.json();
    const latency = Math.round(performance.now() - startedAt);

    if (!response.ok || !envelope.success) {
      throw new Error(envelope?.error?.message || `请求失败 (${response.status})`);
    }

    updateStateAfterSuccess(mode, envelope, latency);
  } catch (error) {
    const actionText = mode === "search" ? "搜索失败" : "详情解析失败";
    setBanner(error.message || "请求失败", actionText, "error");
  } finally {
    setButtonBusy(button, false);
  }
}

function updateStateAfterSuccess(mode, envelope, latency) {
  state.currentJson = envelope;
  updateJsonOutput();
  elements.metricRequestId.textContent = envelope.request_id || "-";

  if (mode === "search") {
    state.searchEnvelope = envelope;
    const items = envelope?.data?.items || [];
    elements.metricSearchCount.textContent = String(items.length);
    elements.searchResultSummary.textContent = `${items.length} 条结果，耗时 ${latency} ms`;
    elements.responseState.textContent = "搜索结果已更新";
    setBanner(`搜索完成，共返回 ${items.length} 条结果。`, "搜索成功", "success");
    renderSearchResults(items);
  } else {
    state.detailEnvelope = envelope;
    elements.metricDetailState.textContent = "已解析";
    elements.detailResultSummary.textContent = `详情已更新，耗时 ${latency} ms`;
    elements.responseState.textContent = "详情结果已更新";
    setBanner("详情解析成功，已更新右侧结果区。", "详情成功", "success");
    renderDetailResult(envelope.data);
  }
}

function renderSearchResults(items) {
  if (!Array.isArray(items) || items.length === 0) {
    elements.searchResults.innerHTML = `
      <div class="empty-state">
        <p>没有返回结果。</p>
        <span>可以尝试调整排序、发布时间或更换 Cookie 后再试。</span>
      </div>
    `;
    return;
  }

  const cards = items
    .map((item) => {
      const authorLink = item.author_profile_url
        ? `<a class="tiny-button" href="${escapeAttribute(item.author_profile_url)}" target="_blank" rel="noreferrer">作者主页</a>`
        : "";
      const parseAction = item.url
        ? `<button type="button" class="tiny-button js-parse-detail" data-url="${escapeAttribute(item.url)}">解析详情</button>`
        : "";

      return `
        <article class="note-card">
          <div class="note-head">
            <div>
              <h5 class="note-title">${escapeHtml(item.title || "未命名笔记")}</h5>
              <ul class="note-meta">
                <li>作者：${escapeHtml(item.author_name || "-")}</li>
                <li>作者ID：${escapeHtml(item.author_id || "-")}</li>
                <li>发布时间：${escapeHtml(formatDateTime(item.publish_time))}</li>
              </ul>
            </div>
            <span class="type-pill">${escapeHtml(noteTypeLabel(item.note_type))}</span>
          </div>
          <div class="stat-grid">
            ${renderStat("点赞", item.liked_count)}
            ${renderStat("收藏", item.collected_count)}
            ${renderStat("评论", item.comment_count)}
          </div>
          <div class="note-actions">
            <a class="tiny-button" href="${escapeAttribute(item.url || "#")}" target="_blank" rel="noreferrer">打开笔记</a>
            ${authorLink}
            ${parseAction}
            <button type="button" class="tiny-button js-copy-link" data-copy="${escapeAttribute(item.url || "")}">复制链接</button>
          </div>
        </article>
      `;
    })
    .join("");

  elements.searchResults.innerHTML = cards;

  elements.searchResults.querySelectorAll(".js-parse-detail").forEach((button) => {
    button.addEventListener("click", async () => {
      const url = button.getAttribute("data-url") || "";
      let cookie = "";
      try {
        cookie = getCookieOrThrow();
      } catch (error) {
        setBanner(error.message || "请先填写 Cookie。", "详情未解析", "error");
        return;
      }
      elements.detailUrl.value = url;
      await submitRequest({
        path: "/api/v1/rednote/detail",
        payload: {
          url,
          cookie,
        },
        button,
        mode: "detail",
      });
    });
  });

  bindCopyButtons(elements.searchResults);
}

function renderDetailResult(detail) {
  if (!detail) {
    elements.detailResult.innerHTML = `
      <div class="empty-state">
        <p>未拿到详情数据。</p>
        <span>请更换链接或检查 Cookie 是否失效。</span>
      </div>
    `;
    return;
  }

  const images = Array.isArray(detail.images) ? detail.images : [];
  const tags = Array.isArray(detail.tags) ? detail.tags : [];
  const mediaLinks = images.length
    ? images
        .map(
          (url, index) =>
            `<a class="media-link" href="${escapeAttribute(url)}" target="_blank" rel="noreferrer">图片 ${index + 1} · ${escapeHtml(url)}</a>`,
        )
        .join("")
    : `<div class="empty-state"><p>未返回图片列表。</p><span>如果原笔记是视频，可能只会返回视频地址。</span></div>`;

  const videoLink = detail.video
    ? `<a class="media-link" href="${escapeAttribute(detail.video)}" target="_blank" rel="noreferrer">视频地址 · ${escapeHtml(detail.video)}</a>`
    : "";

  elements.detailResult.innerHTML = `
    <article class="detail-shell">
      <h4 class="detail-title">${escapeHtml(detail.title || "未命名笔记")}</h4>
      <ul class="detail-meta">
        <li>作者：${escapeHtml(detail.author_name || "-")}</li>
        <li>作者主页：${
          detail.author_profile_url
            ? `<a href="${escapeAttribute(detail.author_profile_url)}" target="_blank" rel="noreferrer">${escapeHtml(detail.author_profile_url)}</a>`
            : "-"
        }</li>
        <li>发布时间：${escapeHtml(formatDateTime(detail.publish_time))}</li>
        <li>最近更新时间：${escapeHtml(formatDateTime(detail.last_update_time))}</li>
      </ul>

      <div class="stat-grid">
        ${renderStat("点赞", detail.liked_count)}
        ${renderStat("收藏", detail.collected_count)}
        ${renderStat("评论", detail.comment_count)}
      </div>
      <div class="stat-grid">
        ${renderStat("分享", detail.share_count)}
        ${renderStat("类型", noteTypeLabel(detail.note_type))}
        ${renderStat("媒体数", String(images.length + (detail.video ? 1 : 0)))}
      </div>

      <p class="detail-desc">${escapeHtml(detail.desc || "暂无正文描述。")}</p>

      <div class="note-actions">
        <a class="tiny-button" href="${escapeAttribute(detail.url || "#")}" target="_blank" rel="noreferrer">打开笔记</a>
        <button type="button" class="tiny-button js-copy-link" data-copy="${escapeAttribute(detail.url || "")}">复制笔记链接</button>
      </div>

      <div class="chip-row">
        ${tags.length ? tags.map((tag) => `<span class="tag-chip">${escapeHtml(tag)}</span>`).join("") : '<span class="tag-chip">暂无标签</span>'}
      </div>

      <div class="media-list">
        ${mediaLinks}
        ${videoLink}
      </div>
    </article>
  `;

  bindCopyButtons(elements.detailResult);
}

function renderStat(label, value) {
  return `
    <div class="stat-item">
      <span class="stat-label">${escapeHtml(label)}</span>
      <span class="stat-value">${escapeHtml(value ?? "-")}</span>
    </div>
  `;
}

function setBanner(message, title, tone) {
  elements.responseBanner.classList.remove("is-error", "is-success");
  elements.responseBanner.classList.add(tone === "error" ? "is-error" : "is-success");
  elements.responseBanner.innerHTML = `
    <strong>${escapeHtml(title)}</strong>
    <span>${escapeHtml(message)}</span>
  `;
}

function setHealthStatus(title, hint, tone) {
  elements.serviceStatus.textContent = title;
  elements.serviceStatus.classList.remove("status-pending", "status-success", "status-error");
  elements.serviceStatus.classList.add(
    tone === "success" ? "status-success" : tone === "error" ? "status-error" : "status-pending",
  );
  elements.serviceLatency.textContent = hint;
}

function setButtonBusy(button, busy) {
  if (!(button instanceof HTMLElement)) {
    return;
  }
  button.setAttribute("aria-busy", busy ? "true" : "false");
  if (button instanceof HTMLButtonElement) {
    button.disabled = busy;
  }
}

function fillSearchDemo() {
  document.getElementById("search-keyword").value = SEARCH_DEMO.keyword;
  document.getElementById("search-note-type").value = SEARCH_DEMO.note_type;
  document.getElementById("search-publish-time").value = SEARCH_DEMO.publish_time;
  document.getElementById("search-sort-by").value = SEARCH_DEMO.sort_by;
  document.getElementById("search-page-count").value = String(SEARCH_DEMO.page_count);
}

function fillDetailDemo() {
  elements.detailUrl.value = DETAIL_DEMO_URL;
}

function getBaseUrl() {
  return normalizeBaseUrl(elements.baseUrl.value);
}

function normalizeBaseUrl(value) {
  const trimmed = (value || "").trim();
  if (!trimmed) {
    return window.location.origin || "http://127.0.0.1:8000";
  }
  return trimmed.replace(/\/+$/, "");
}

function getCookieOrThrow() {
  const cookie = elements.sharedCookie.value.trim();
  if (!cookie) {
    throw new Error("请先在“统一会话配置”里填写 Cookie。");
  }
  return cookie;
}

async function copyCurrentJson() {
  const text = state.currentJson
    ? JSON.stringify(state.currentJson, null, 2)
    : elements.jsonOutput.textContent || "";
  await copyText(text, "已复制当前 JSON。");
}

function updateJsonOutput() {
  elements.jsonOutput.textContent = JSON.stringify(state.currentJson, null, 2);
}

function bindCopyButtons(container) {
  container.querySelectorAll(".js-copy-link").forEach((button) => {
    button.addEventListener("click", async () => {
      const text = button.getAttribute("data-copy") || "";
      await copyText(text, "已复制链接。");
    });
  });
}

async function copyText(text, successMessage) {
  if (!text) {
    setBanner("当前没有可复制的内容。", "复制失败", "error");
    return;
  }

  try {
    await navigator.clipboard.writeText(text);
    setBanner(successMessage, "复制成功", "success");
  } catch (error) {
    setBanner("浏览器未授予剪贴板权限，请手动复制。", "复制失败", "error");
  }
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function escapeAttribute(value) {
  return escapeHtml(value).replace(/`/g, "&#96;");
}

function formatDateTime(value) {
  if (!value) {
    return "-";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
    hour12: false,
  }).format(date);
}

function noteTypeLabel(value) {
  if (value === "image") {
    return "图文";
  }
  if (value === "video") {
    return "视频";
  }
  return "默认";
}

window.addEventListener("DOMContentLoaded", init);
