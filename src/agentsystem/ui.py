from __future__ import annotations

from html import escape
import json
from pathlib import Path


def render_index() -> str:
    default_workspace = str(Path.cwd())
    return """<!doctype html>
<html lang="zh-CN" class="notranslate" translate="no" data-theme="dark">
<head>
  <meta charset="utf-8">
  <meta name="google" content="notranslate">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AgentSystem 控制台</title>
  <script>
    try {
      const savedTheme = localStorage.getItem('agentsystem-theme');
      document.documentElement.dataset.theme = savedTheme === 'light' ? 'light' : 'dark';
      const savedLanguage = localStorage.getItem('agentsystem-language');
      document.documentElement.dataset.language = savedLanguage === 'en' ? 'en' : 'zh';
      document.documentElement.lang = savedLanguage === 'en' ? 'en' : 'zh-CN';
    } catch (_) {
      document.documentElement.dataset.theme = 'dark';
      document.documentElement.dataset.language = 'zh';
      document.documentElement.lang = 'zh-CN';
    }
  </script>
  <style>
    :root {
      color-scheme: dark;
      --bg: #050812;
      --nav: #070b14;
      --surface: #0b1220;
      --surface-2: #101827;
      --surface-3: #131e31;
      --line: #22304a;
      --line-2: #334563;
      --text: #edf4ff;
      --muted: #91a2ba;
      --soft: #cbd8ea;
      --blue: #56a6ff;
      --green: #4fda8b;
      --violet: #9b72ff;
      --amber: #f3b64b;
      --red: #ff7070;
      --shadow: 0 22px 70px rgba(0, 0, 0, 0.34);
      --radius: 8px;
      --app-bg:
        radial-gradient(circle at 50% 0%, rgba(76, 116, 204, 0.17), transparent 32%),
        linear-gradient(180deg, #080d18, #04070e);
      --topbar-bg: rgba(5, 9, 18, 0.92);
      --nav-bg: rgba(5, 9, 18, 0.88);
      --button-bg: #111a2b;
      --button-hover-bg: #172238;
      --input-bg: #070d18;
      --pill-bg: rgba(13, 21, 35, 0.92);
      --panel-bg: rgba(11, 18, 32, 0.94);
      --card-bg: rgba(9, 16, 29, 0.78);
      --card-soft-bg: rgba(13, 22, 37, 0.82);
      --column-bg: rgba(6, 12, 22, 0.58);
      --flow-bg: #070c16;
      --flow-dot: rgba(148, 163, 184, 0.13);
      --flow-path: rgba(141, 128, 255, 0.78);
      --flow-card-bg: linear-gradient(180deg, rgba(18, 27, 45, 0.98), rgba(8, 14, 25, 0.98));
      --mark-bg: rgba(118, 107, 255, 0.13);
      --selected-bg: rgba(86, 166, 255, 0.1);
      --approval-bg: rgba(243, 182, 75, 0.08);
      --message-assistant-bg: rgba(86, 166, 255, 0.1);
      --preview-bg: #050a13;
      --toast-bg: #101827;
      --heading-text: #f8fbff;
      --workspace-head-bg: rgba(8, 13, 24, 0.72);
      --tag-bg: rgba(13, 22, 37, 0.76);
      --danger-text: #ffd4d4;
      --danger-border: rgba(255, 112, 112, 0.45);
      --focus-ring: #9b8cff;
      --focus-shadow: rgba(118, 107, 255, 0.15);
      --primary-bg: #4f46e5;
      --primary-border: #786dff;
      --status-idle: #65758e;
      --ring-track: rgba(148, 163, 184, 0.16);
      --ring-text: #e6fff0;
      --event-time: #7f8fa8;
      --event-actor: #cfc4ff;
      --event-type: #93c7ff;
      --preview-text: #d9e6f7;
      --nav-active-text: #d6ccff;
      --nav-active-bg: rgba(118, 86, 255, 0.16);
      --nav-active-border: rgba(151, 125, 255, 0.4);
    }

    :root[data-theme="light"] {
      color-scheme: light;
      --bg: #f4f7fb;
      --nav: #edf2f9;
      --surface: #ffffff;
      --surface-2: #f5f8fc;
      --surface-3: #eaf1f9;
      --line: #d6dfec;
      --line-2: #aebcd0;
      --text: #122033;
      --muted: #607087;
      --soft: #2f435d;
      --blue: #0b72d9;
      --green: #087a45;
      --violet: #6844d9;
      --amber: #9a6200;
      --red: #c43d3d;
      --shadow: 0 18px 48px rgba(30, 48, 74, 0.13);
      --app-bg:
        radial-gradient(circle at 50% 0%, rgba(79, 122, 202, 0.14), transparent 34%),
        linear-gradient(180deg, #f7faff, #eef4fb);
      --topbar-bg: rgba(255, 255, 255, 0.92);
      --nav-bg: rgba(246, 249, 253, 0.92);
      --button-bg: #ffffff;
      --button-hover-bg: #eef4fb;
      --input-bg: #ffffff;
      --pill-bg: rgba(255, 255, 255, 0.92);
      --panel-bg: rgba(255, 255, 255, 0.94);
      --card-bg: rgba(255, 255, 255, 0.86);
      --card-soft-bg: rgba(244, 248, 253, 0.92);
      --column-bg: rgba(248, 251, 255, 0.72);
      --flow-bg: #f8fbff;
      --flow-dot: rgba(86, 105, 130, 0.18);
      --flow-path: rgba(91, 78, 200, 0.7);
      --flow-card-bg: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(241, 246, 252, 0.98));
      --mark-bg: rgba(104, 68, 217, 0.1);
      --selected-bg: rgba(11, 114, 217, 0.1);
      --approval-bg: rgba(154, 98, 0, 0.08);
      --message-assistant-bg: rgba(11, 114, 217, 0.08);
      --preview-bg: #f9fbfe;
      --toast-bg: #ffffff;
      --heading-text: #102033;
      --workspace-head-bg: rgba(255, 255, 255, 0.7);
      --tag-bg: rgba(239, 245, 252, 0.9);
      --danger-text: #9f2424;
      --danger-border: rgba(196, 61, 61, 0.38);
      --focus-ring: #6844d9;
      --focus-shadow: rgba(104, 68, 217, 0.14);
      --primary-bg: #5a45e8;
      --primary-border: #7b68f0;
      --status-idle: #8794a7;
      --ring-track: rgba(90, 105, 125, 0.18);
      --ring-text: #ffffff;
      --event-time: #657489;
      --event-actor: #5a3dbd;
      --event-type: #0b62ba;
      --preview-text: #17304c;
      --nav-active-text: #3f2ea7;
      --nav-active-bg: rgba(104, 68, 217, 0.12);
      --nav-active-border: rgba(104, 68, 217, 0.28);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      height: 100vh;
      overflow: hidden;
      background: var(--bg);
      color: var(--text);
      font: 13px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    button, input, select, textarea { font: inherit; }

    button {
      min-height: 36px;
      padding: 0 11px;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: var(--button-bg);
      color: var(--text);
      cursor: pointer;
      transition: background-color 160ms ease, border-color 160ms ease, opacity 160ms ease;
    }

    button:hover { background: var(--button-hover-bg); border-color: var(--line-2); }
    button.primary { background: var(--primary-bg); border-color: var(--primary-border); color: white; }
    button.danger { color: var(--danger-text); border-color: var(--danger-border); }
    button.ghost { background: transparent; }
    button.icon { width: 32px; padding: 0; display: inline-grid; place-items: center; }
    button[disabled] { opacity: 0.45; cursor: not-allowed; }

    input, select, textarea {
      width: 100%;
      min-height: 34px;
      padding: 8px 10px;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: var(--input-bg);
      color: var(--text);
      outline: none;
    }

    textarea { min-height: 88px; resize: vertical; }
    input:focus, select:focus, textarea:focus { border-color: var(--focus-ring); box-shadow: 0 0 0 3px var(--focus-shadow); }
    button:focus-visible, input:focus-visible, select:focus-visible, textarea:focus-visible {
      outline: 2px solid var(--focus-ring);
      outline-offset: 2px;
    }
    label { display: grid; gap: 6px; color: var(--soft); font-size: 12px; }
    code, pre, .mono { font-family: "SFMono-Regular", Consolas, monospace; }
    pre { margin: 0; white-space: pre-wrap; overflow-wrap: anywhere; }

    .app {
      height: 100vh;
      display: grid;
      grid-template-columns: 86px minmax(0, 1fr);
      grid-template-rows: 62px minmax(0, 1fr);
      background: var(--app-bg);
    }

    .topbar {
      grid-column: 1 / -1;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      min-width: 0;
      padding: 0 16px;
      border-bottom: 1px solid var(--line);
      background: var(--topbar-bg);
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      min-width: 0;
    }

    .logo {
      width: 30px;
      height: 30px;
      display: grid;
      place-items: center;
      border-radius: 8px;
      background: linear-gradient(135deg, var(--blue), var(--violet) 55%, var(--green));
      color: white;
      font-weight: 900;
      box-shadow: 0 0 30px rgba(86, 166, 255, 0.36);
    }

    .brand h1 {
      margin: 0;
      font-size: 14px;
      letter-spacing: 0.04em;
      white-space: nowrap;
    }

    .brand small { color: var(--muted); white-space: nowrap; }

    .top-metrics {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 8px;
      min-width: 0;
      flex-wrap: wrap;
    }

    .pill {
      display: inline-flex;
      align-items: center;
      gap: 7px;
      min-height: 28px;
      padding: 4px 9px;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: var(--pill-bg);
      color: var(--soft);
      white-space: nowrap;
    }

    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 999px;
      background: var(--status-idle);
    }

    .status-dot.completed, .status-dot.ok { background: var(--green); box-shadow: 0 0 10px rgba(79, 218, 139, 0.75); }
    .status-dot.running { background: var(--blue); box-shadow: 0 0 10px rgba(86, 166, 255, 0.75); }
    .status-dot.awaiting_approval { background: var(--amber); box-shadow: 0 0 10px rgba(243, 182, 75, 0.65); }
    .status-dot.failed { background: var(--red); box-shadow: 0 0 10px rgba(255, 112, 112, 0.62); }
    .status-dot.pending { background: #9aa9bf; }

    .nav {
      grid-row: 2;
      min-height: 0;
      padding: 12px 8px;
      border-right: 1px solid var(--line);
      background: var(--nav-bg);
      overflow: auto;
    }

    .nav-list {
      display: grid;
      gap: 8px;
    }

    .nav-button {
      width: 100%;
      min-height: 58px;
      display: grid;
      place-items: center;
      gap: 4px;
      padding: 6px;
      border-color: transparent;
      background: transparent;
      color: var(--muted);
      font-size: 11px;
    }

    .nav-button strong { font-size: 17px; line-height: 1; }
    .nav-button.active {
      color: var(--nav-active-text);
      background: var(--nav-active-bg);
      border-color: var(--nav-active-border);
    }

    .main {
      grid-row: 2;
      min-width: 0;
      min-height: 0;
      overflow: hidden;
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
    }

    .workspace-head {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 12px;
      align-items: center;
      padding: 14px 18px;
      border-bottom: 1px solid var(--line);
      background: var(--workspace-head-bg);
    }

    .workspace-title {
      min-width: 0;
      display: grid;
      gap: 3px;
    }

    .workspace-title h2 {
      margin: 0;
      font-size: 19px;
      letter-spacing: 0;
    }

    .workspace-title p {
      margin: 0;
      color: var(--muted);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .workspace-actions {
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
      justify-content: flex-end;
    }

    .views {
      min-height: 0;
      overflow: hidden;
      position: relative;
    }

    .view {
      display: none;
      height: 100%;
      overflow: auto;
      padding: 16px;
    }

    .view.active { display: block; }

    .grid {
      display: grid;
      gap: 12px;
    }

    .grid.two { grid-template-columns: minmax(0, 1.15fr) minmax(360px, 0.85fr); }
    .grid.three { grid-template-columns: repeat(3, minmax(0, 1fr)); }
    .grid.four { grid-template-columns: repeat(4, minmax(0, 1fr)); }
    .grid.board { grid-template-columns: 360px minmax(0, 1fr); align-items: start; }
    .grid.split { grid-template-columns: minmax(320px, 0.7fr) minmax(0, 1.3fr); align-items: start; }

    .panel {
      min-width: 0;
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: var(--panel-bg);
      box-shadow: var(--shadow);
    }

    .panel-head {
      min-height: 46px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      padding: 12px 14px;
      border-bottom: 1px solid var(--line);
    }

    .panel-title {
      font-size: 12px;
      font-weight: 850;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--heading-text);
    }

    .panel-subtitle { color: var(--muted); font-size: 12px; overflow-wrap: anywhere; }
    .panel-body { padding: 12px; min-width: 0; }

    .stat {
      display: grid;
      gap: 8px;
      padding: 13px;
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: var(--card-soft-bg);
    }

    .stat span { color: var(--muted); }
    .stat strong { font-size: 20px; line-height: 1.1; overflow-wrap: anywhere; }

    .flow-canvas {
      position: relative;
      height: 520px;
      overflow: hidden;
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background-color: var(--flow-bg);
      background-image: radial-gradient(circle, var(--flow-dot) 1px, transparent 1px);
      background-size: 18px 18px;
    }

    .flow-line {
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      pointer-events: none;
      opacity: 0.85;
    }

    .flow-line path {
      fill: none;
      stroke: var(--flow-path);
      stroke-width: 2.2;
      filter: drop-shadow(0 0 6px rgba(141, 128, 255, 0.45));
      vector-effect: non-scaling-stroke;
    }

    .flow-card {
      position: absolute;
      left: var(--x);
      top: var(--y);
      width: 180px;
      transform: translate(-50%, -50%);
      display: grid;
      grid-template-columns: 38px minmax(0, 1fr) auto;
      gap: 9px;
      align-items: center;
      padding: 10px;
      border: 1px solid var(--accent, var(--line-2));
      border-radius: 8px;
      background: var(--flow-card-bg);
      color: var(--text);
      box-shadow: 0 0 24px rgba(113, 102, 255, 0.14);
      cursor: pointer;
    }

    .flow-card.selected { border-width: 2px; box-shadow: 0 0 30px rgba(113, 102, 255, 0.28); }

    .mark {
      width: 34px;
      height: 34px;
      display: grid;
      place-items: center;
      border: 1px solid var(--accent, var(--line-2));
      border-radius: 8px;
      background: var(--mark-bg);
      color: var(--accent, var(--blue));
      font-weight: 900;
    }

    .flow-main, .truncate { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .flow-main strong, .item-title { display: block; color: var(--heading-text); font-weight: 760; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .flow-main span, .item-meta { color: var(--muted); font-size: 12px; overflow-wrap: anywhere; }

    .ring {
      width: 34px;
      height: 34px;
      display: grid;
      place-items: center;
      border-radius: 999px;
      background: conic-gradient(var(--green) var(--progress, 20%), var(--ring-track) 0);
      color: var(--ring-text);
      font-size: 10px;
      font-weight: 900;
    }

    .list {
      display: grid;
      gap: 8px;
      min-width: 0;
    }

    .item {
      display: grid;
      gap: 6px;
      min-width: 0;
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: var(--card-bg);
    }

    button.item { text-align: left; }
    .item.selected { border-color: rgba(86, 166, 255, 0.65); background: var(--selected-bg); }
    .item-row { display: flex; align-items: center; justify-content: space-between; gap: 10px; min-width: 0; }

    .tag {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      min-height: 24px;
      padding: 2px 7px;
      border: 1px solid var(--line);
      border-radius: 999px;
      color: var(--soft);
      background: var(--tag-bg);
      font-size: 11px;
      white-space: nowrap;
    }

    .task-board {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 12px;
    }

    .column {
      display: grid;
      align-content: start;
      gap: 8px;
      min-height: 260px;
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: var(--column-bg);
    }

    .column h3 {
      margin: 0 0 4px;
      font-size: 12px;
      text-transform: uppercase;
      color: var(--muted);
      letter-spacing: 0.05em;
    }

    .form {
      display: grid;
      gap: 10px;
    }

    .form-row {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }

    .path-display {
      display: grid;
      gap: 6px;
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: var(--card-soft-bg);
    }

    .path-display strong {
      color: var(--soft);
      font-size: 12px;
      font-weight: 600;
    }

    .path-display code {
      color: var(--text);
      overflow-wrap: anywhere;
    }

    .toolbar {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }

    .approval {
      border-color: rgba(243, 182, 75, 0.44);
      background: var(--approval-bg);
    }

    .chat-log, .event-list, .file-list, .artifact-list {
      max-height: 430px;
      overflow: auto;
    }

    .message {
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: var(--card-bg);
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }

    .message.assistant { border-color: rgba(86, 166, 255, 0.34); background: var(--message-assistant-bg); }
    .message.user { border-color: rgba(155, 114, 255, 0.34); }

    .event-row {
      display: grid;
      grid-template-columns: 82px 132px 144px minmax(0, 1fr);
      gap: 10px;
      align-items: start;
      padding: 5px 0;
      color: var(--soft);
      font-size: 12px;
    }

    .event-time { color: var(--event-time); }
    .event-actor { color: var(--event-actor); font-weight: 760; }
    .event-type { color: var(--event-type); }
    .event-body { overflow-wrap: anywhere; }

    .file-browser {
      display: grid;
      grid-template-columns: minmax(260px, 0.85fr) minmax(0, 1.15fr);
      gap: 12px;
      align-items: start;
    }

    .file-button {
      display: grid;
      grid-template-columns: auto minmax(0, 1fr) auto;
      gap: 8px;
      align-items: center;
      width: 100%;
      text-align: left;
    }

    .preview {
      max-height: 560px;
      overflow: auto;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: var(--preview-bg);
      color: var(--preview-text);
      font-size: 12px;
    }

    .model-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 10px;
    }

    .arch-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 12px;
    }

    .empty {
      padding: 18px;
      border: 1px dashed var(--line);
      border-radius: var(--radius);
      color: var(--muted);
      text-align: center;
    }

    .toast {
      position: fixed;
      right: 18px;
      bottom: 18px;
      z-index: 20;
      max-width: 460px;
      padding: 11px 13px;
      border: 1px solid var(--line-2);
      border-radius: var(--radius);
      background: var(--toast-bg);
      box-shadow: var(--shadow);
      opacity: 0;
      transform: translateY(10px);
      pointer-events: none;
      transition: 160ms ease;
    }

    .toast.show { opacity: 1; transform: translateY(0); }

    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        scroll-behavior: auto !important;
        transition-duration: 0.01ms !important;
      }
    }

    @media (max-width: 1320px) {
      body { overflow: auto; }
      .app {
        height: auto;
        min-height: 100vh;
        grid-template-columns: 76px minmax(0, 1fr);
      }
      .grid.two, .grid.board, .grid.split, .file-browser { grid-template-columns: 1fr; }
      .grid.three, .grid.four, .task-board { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .view { min-height: calc(100vh - 118px); }
    }

    @media (max-width: 780px) {
      .app { display: block; }
      .topbar { align-items: flex-start; padding: 12px; }
      .nav { border-right: 0; border-bottom: 1px solid var(--line); }
      .nav-list { grid-template-columns: repeat(4, 1fr); }
      .workspace-head { grid-template-columns: 1fr; }
      .grid.three, .grid.four, .task-board, .form-row { grid-template-columns: 1fr; }
      .event-row { grid-template-columns: 78px minmax(0, 1fr); }
      .flow-card { width: 164px; }
    }

    @media (max-width: 900px) {
      .flow-canvas {
        height: auto;
        min-height: 0;
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
        align-content: start;
        gap: 10px;
        padding: 54px 12px 12px;
      }

      .flow-line { display: none; }

      .flow-card {
        position: static;
        width: 100%;
        transform: none;
      }

      .flow-canvas > .tag {
        left: 12px !important;
        top: 12px !important;
      }
    }
  </style>
</head>
<body>
  <div class="app">
    <header class="topbar">
      <div class="brand">
        <div class="logo">A</div>
        <div>
          <h1>AgentSystem 控制台</h1>
          <small>私有化代码协作多 Agent 平台</small>
        </div>
      </div>
      <div class="top-metrics">
        <span class="pill"><span class="status-dot ok"></span><span id="topRunState">READY</span></span>
        <span class="pill"><span data-copy-key="top.tasks">任务</span> <strong id="topTaskCount">0</strong></span>
        <span class="pill"><span data-copy-key="top.approvals">审批</span> <strong id="topApprovalCount">0</strong></span>
        <span class="pill"><span data-copy-key="top.model">模型</span> <strong id="topModelName">loading</strong></span>
        <button class="ghost" id="themeToggle" type="button" aria-label="切换白天黑夜模式" aria-pressed="false">白天</button>
        <button class="ghost" id="refreshBtn" data-copy-key="actions.refresh">刷新</button>
      </div>
    </header>

    <nav class="nav" aria-label="模块导航">
      <div class="nav-list">
        <button class="nav-button active" data-view="overview" aria-label="总览模块"><strong>O</strong><span>总览</span></button>
        <button class="nav-button" data-view="tasks" aria-label="任务模块"><strong>T</strong><span>任务</span></button>
        <button class="nav-button" data-view="agents" aria-label="智能体模块"><strong>A</strong><span>智能体</span></button>
        <button class="nav-button" data-view="workspace" aria-label="工作区模块"><strong>W</strong><span>工作区</span></button>
        <button class="nav-button" data-view="models" aria-label="模型模块"><strong>M</strong><span>模型</span></button>
        <button class="nav-button" data-view="logs" aria-label="日志模块"><strong>L</strong><span>日志</span></button>
        <button class="nav-button" data-view="architecture" aria-label="架构模块"><strong>X</strong><span>架构</span></button>
        <button class="nav-button" data-view="settings" aria-label="设置模块"><strong>S</strong><span>设置</span></button>
      </div>
    </nav>

    <main class="main">
      <div class="workspace-head">
        <div class="workspace-title">
          <h2 id="viewTitle">总览</h2>
          <p id="viewSubtitle">模块化工作台</p>
        </div>
        <div class="workspace-actions">
          <button class="ghost" data-view-jump="tasks" data-copy-key="actions.createTask">创建任务</button>
          <button class="ghost" data-view-jump="workspace" data-copy-key="actions.localProject">本地项目</button>
          <button class="primary" data-view-jump="models" data-copy-key="actions.agentModelRoute">Agent 模型路由</button>
        </div>
      </div>

      <div class="views">
        <section class="view active" id="view-overview"></section>
        <section class="view" id="view-tasks"></section>
        <section class="view" id="view-agents"></section>
        <section class="view" id="view-workspace"></section>
        <section class="view" id="view-models"></section>
        <section class="view" id="view-logs"></section>
        <section class="view" id="view-architecture"></section>
        <section class="view" id="view-settings"></section>
      </div>
    </main>
  </div>
  <div class="toast" id="toast" aria-live="polite"></div>

  <script>
    const DEFAULT_WORKSPACE = __DEFAULT_WORKSPACE_JSON__;
    const AGENTS = {
      orchestrator: { label: 'Orchestrator', role: 'Mission Control', mark: 'O', accent: '#9b72ff', x: '50%', y: '15%' },
      repo_context: { label: 'Repo Context', role: 'Code Intelligence', mark: 'R', accent: '#56a6ff', x: '22%', y: '36%' },
      planning: { label: 'Planning', role: 'Strategy', mark: 'P', accent: '#9b72ff', x: '50%', y: '36%' },
      coding: { label: 'Coding', role: 'Code Synthesis', mark: 'C', accent: '#4fda8b', x: '78%', y: '36%' },
      security: { label: 'Security', role: 'Guardrails', mark: 'S', accent: '#f3b64b', x: '30%', y: '61%' },
      test: { label: 'Test', role: 'Verification', mark: 'T', accent: '#56a6ff', x: '64%', y: '61%' },
      review: { label: 'Review', role: 'Code Review', mark: 'V', accent: '#ff8a65', x: '35%', y: '83%' },
      pr: { label: 'PR', role: 'Draft PR', mark: 'G', accent: '#4fda8b', x: '72%', y: '83%' }
    };
    const AGENT_ORDER = Object.keys(AGENTS);
    const LANGUAGE_STORAGE_KEY = 'agentsystem-language';
    const COPY = {
      zh: {
        htmlLang: 'zh-CN',
        navAria: '模块导航',
        moduleSuffix: '模块',
        top: { ready: '就绪', running: '运行中', tasks: '任务', approvals: '审批', model: '模型', notConfigured: '未配置' },
        actions: {
          createTask: '创建任务',
          localProject: '本地项目',
          agentModelRoute: 'Agent 模型路由',
          refresh: '刷新',
          openTask: '打开任务',
          approve: '批准',
          trace: 'Trace',
          viewAll: '查看全部',
          reload: '重新加载',
          cancel: '取消',
          send: '发送',
          configureModel: '配置模型',
          openFolder: '打开文件夹',
          selectProjectFolder: '选择项目目录',
          root: '根目录',
          showInFinder: '在 Finder 显示',
          taskFromWorkspace: '从工作区创建任务',
          saveAgentRoute: '保存 Agent 路由',
          check: '检查'
        },
        theme: {
          dayButton: '白天',
          nightButton: '夜间',
          title: label => `切换到${label}模式`,
          switched: mode => `已切换到${mode}模式`
        },
        language: {
          zh: '中文',
          en: 'English',
          switched: '已切换到中文界面',
          switchedEn: 'Switched to English interface'
        },
        views: {
          overview: ['总览', '系统态势、当前任务和 Agent 编排总览'],
          tasks: ['任务', '任务创建、审批、产物与 AI 协作对话'],
          agents: ['智能体', 'Agent 工作状态、目标、输出和 handoff'],
          workspace: ['工作区', '本地项目文件夹、文件预览与任务绑定'],
          models: ['模型', '每个 Agent 的 provider/model/API key 环境变量配置'],
          logs: ['日志', 'Trace、模型调用、工具调用、审计与聊天事件'],
          architecture: ['架构', '平台分层、服务边界和落地状态'],
          settings: ['设置', '语言、审批策略、安全策略与集成状态']
        },
        overview: {
          totalTasks: '任务总数',
          running: '执行中',
          awaitingApproval: '待人工确认',
          completed: '已完成',
          workflowCanvas: '工作流画布',
          workflowSubtitle: '多 Agent 协同编排',
          currentTask: '当前任务',
          noActiveTask: '暂无活动任务',
          noTask: '还没有任务。去任务区域创建一个工作流。',
          recentOutput: '最近 Agent 输出',
          outputSubtitle: '各个 Agent 信息输出在控制台'
        },
        tasks: {
          createTitle: '创建任务',
          createSubtitle: '创建任务',
          repoId: '仓库 ID',
          prompt: '需求 / Issue',
          promptPlaceholder: '描述要让多 Agent 协作完成的代码任务',
          promptDefault: '基于本地项目检查多 Agent 代码协作工作流，并输出计划',
          baseBranch: '基础分支',
          priority: '优先级',
          approvalPolicy: '审批策略',
          launch: '启动工作流',
          boardTitle: '任务看板',
          boardSubtitle: '按状态管理任务',
          detailTitle: '任务详情',
          noTaskSelected: '未选择任务',
          emptyColumn: '暂无',
          noPendingApproval: '暂无待审批项',
          noWorkspaceBound: '未绑定工作区',
          artifacts: '产物',
          artifactsSubtitle: '计划、上下文、报告',
          noArtifacts: '暂无产物',
          aiCollaboration: 'AI 协作',
          aiSubtitle: 'AI 协作对话',
          chatPlaceholder: '例如：让 coding 定位文件，让 review 看风险，让 planning 改计划...',
          selectOrCreate: '选择或创建任务后，这里会显示审批、产物和 AI 协作对话。'
        },
        taskColumns: {
          created: '已创建',
          running: '运行中',
          approval: '待审批',
          done: '完成',
          stopped: '停止'
        },
        agents: {
          roster: 'Agent 队列',
          rosterSubtitle: 'Agent 工作状态',
          inspector: 'Agent 检查器',
          status: '状态',
          latency: '延迟',
          handoff: 'Handoff',
          currentStatus: '当前状态',
          lastRun: '最近运行',
          nextAgent: '下一 Agent',
          objective: '当前目标',
          modelProfile: '模型配置',
          events: 'Agent 事件',
          present: '已配置',
          missing: '缺失',
          enabled: '已启用',
          simulated: '模拟'
        },
        workspace: {
          title: '本地项目',
          projectPath: '项目目录',
          selectedProjectPath: '已选择项目目录',
          currentDir: '当前目录',
          files: '文件',
          noWorkspace: '未打开工作区',
          preview: '预览',
          selectTextFile: '选择文本文件',
          openFirst: '先打开本地项目文件夹。',
          noFiles: '暂无文件'
        },
        models: {
          matrix: 'Agent 模型矩阵',
          matrixSubtitle: 'Agent 模型路由',
          editor: '路由编辑器',
          provider: 'Provider',
          model: 'Model',
          apiKeyEnv: 'API Key 环境变量名',
          baseUrl: 'Base URL',
          callsEnabled: '记录为可真实调用配置',
          hint: '不保存真实 API key，只保存环境变量名；当前网关仍使用模拟响应，不会发起外部模型调用。',
          ready: '就绪',
          simulated: '模拟',
          present: '已配置',
          missing: '缺失'
        },
        logs: {
          title: 'Trace 事件流',
          noEvents: '暂无事件'
        },
        architecture: {
          layers: [
            ['接入层', 'Web 控制台、CLI、GitHub Webhook、REST API', '已实现：Web + REST + webhook stub'],
            ['核心服务', 'api-service、workflow-service、agent-runtime、tool-executor', '已实现：FastAPI + 内存工作流/运行时'],
            ['数据层', 'PostgreSQL、Redis、MinIO、OpenSearch、pgvector', 'MVP：内存存储与产物记录'],
            ['模型层', 'Model Gateway、provider 路由、每 Agent API key 环境变量', '已实现：模拟网关 + 路由编辑器'],
            ['执行层', '隔离 workspace、任务分支、工具策略', 'MVP：本地 workspace + 策略检查'],
            ['观测层', 'trace、审计日志、模型/工具/聊天事件', '已实现：事件流与 trace 端点']
          ]
        },
        settings: {
          languageTitle: '语言',
          languageSubtitle: '系统界面语言',
          languageLabel: '界面语言',
          languageHint: '语言设置会保存在当前浏览器中，刷新后仍然生效。',
          policy: '策略',
          policySubtitle: '审批与安全策略',
          planApproval: '计划审批',
          planApprovalText: 'manual_plan 默认在 Planning 后进入人工审批。',
          secretGuard: '密钥保护',
          secretGuardText: '模型配置拒绝疑似真实 API key，只接受环境变量名。',
          sandboxMode: '沙箱模式',
          sandboxModeText: '工具调用通过 SecurityPolicy 与 ToolExecutor 统一审计。',
          health: '集成健康度',
          healthSubtitle: '运行状态',
          adapterConfigured: '适配器已配置',
          simulated: '模拟'
        },
        toast: {
          taskCanceled: '任务已取消',
          finderOpened: '已在 Finder 打开项目',
          revealUnsupported: '当前系统不支持打开文件夹',
          pickerCanceled: '已取消选择项目目录',
          pickerUnsupported: '当前系统不支持文件夹选择器',
          healthComplete: '健康检查完成',
          taskCreated: '任务已创建',
          workspaceOpened: '本地项目已打开',
          modelSaved: '模型路由已保存',
          selectTaskFirst: '请先选择任务',
          agentReplied: 'Agent 已回复'
        }
      },
      en: {
        htmlLang: 'en',
        navAria: 'Module navigation',
        moduleSuffix: 'module',
        top: { ready: 'READY', running: 'RUNNING', tasks: 'Tasks', approvals: 'Approvals', model: 'Model', notConfigured: 'not configured' },
        actions: {
          createTask: 'Create Task',
          localProject: 'Local Project',
          agentModelRoute: 'Agent Model Routes',
          refresh: 'Refresh',
          openTask: 'Open Task',
          approve: 'Approve',
          trace: 'Trace',
          viewAll: 'View All',
          reload: 'Reload',
          cancel: 'Cancel',
          send: 'Send',
          configureModel: 'Configure Model',
          openFolder: 'Open Folder',
          selectProjectFolder: 'Select Project Folder',
          root: 'Root',
          showInFinder: 'Show in Finder',
          taskFromWorkspace: 'Create Task From Workspace',
          saveAgentRoute: 'Save Agent Route',
          check: 'Check'
        },
        theme: {
          dayButton: 'Light',
          nightButton: 'Dark',
          title: label => `Switch to ${label} mode`,
          switched: mode => `Switched to ${mode} mode`
        },
        language: {
          zh: '中文',
          en: 'English',
          switched: '已切换到中文界面',
          switchedEn: 'Switched to English interface'
        },
        views: {
          overview: ['Overview', 'System posture, current tasks, and agent orchestration'],
          tasks: ['Tasks', 'Task creation, approvals, artifacts, and AI collaboration'],
          agents: ['Agents', 'Agent status, objectives, output, and handoffs'],
          workspace: ['Workspace', 'Local project folder, file preview, and task binding'],
          models: ['Models', 'Provider/model/API key env configuration per Agent'],
          logs: ['Logs', 'Trace, model calls, tool calls, audit, and chat events'],
          architecture: ['Architecture', 'Platform layers, service boundaries, and MVP status'],
          settings: ['Settings', 'Language, approval policy, security policy, and integrations']
        },
        overview: {
          totalTasks: 'Total Tasks',
          running: 'Running',
          awaitingApproval: 'Awaiting Approval',
          completed: 'Completed',
          workflowCanvas: 'Workflow Canvas',
          workflowSubtitle: 'Multi-agent orchestration',
          currentTask: 'Current Task',
          noActiveTask: 'No active task',
          noTask: 'No tasks yet. Create a workflow in Tasks.',
          recentOutput: 'Recent Agent Output',
          outputSubtitle: 'Agent output streams into the console'
        },
        tasks: {
          createTitle: 'Create Task',
          createSubtitle: 'Create Task',
          repoId: 'Repo ID',
          prompt: 'Requirement / Issue',
          promptPlaceholder: 'Describe the code task for multi-agent collaboration',
          promptDefault: 'Inspect the local project multi-agent code collaboration workflow and produce a plan',
          baseBranch: 'Base Branch',
          priority: 'Priority',
          approvalPolicy: 'Approval Policy',
          launch: 'Launch Workflow',
          boardTitle: 'Task Board',
          boardSubtitle: 'Manage tasks by status',
          detailTitle: 'Task Detail',
          noTaskSelected: 'No task selected',
          emptyColumn: 'Empty',
          noPendingApproval: 'No pending approval',
          noWorkspaceBound: 'No workspace bound',
          artifacts: 'Artifacts',
          artifactsSubtitle: 'Plans, context, and reports',
          noArtifacts: 'No artifacts yet',
          aiCollaboration: 'AI Collaboration',
          aiSubtitle: 'AI collaboration chat',
          chatPlaceholder: 'Example: ask coding to locate files, review to check risk, planning to revise the plan...',
          selectOrCreate: 'Select or create a task to see approvals, artifacts, and AI collaboration chat.'
        },
        taskColumns: {
          created: 'Created',
          running: 'Running',
          approval: 'Approval',
          done: 'Done',
          stopped: 'Stopped'
        },
        agents: {
          roster: 'Agent Roster',
          rosterSubtitle: 'Agent status',
          inspector: 'Agent Inspector',
          status: 'Status',
          latency: 'Latency',
          handoff: 'Handoff',
          currentStatus: 'Current status',
          lastRun: 'Last run',
          nextAgent: 'Next Agent',
          objective: 'Current Objective',
          modelProfile: 'Model Profile',
          events: 'Agent Events',
          present: 'present',
          missing: 'missing',
          enabled: 'enabled',
          simulated: 'simulated'
        },
        workspace: {
          title: 'Local Project',
          projectPath: 'Project Path',
          selectedProjectPath: 'Selected Project Path',
          currentDir: 'Current Directory',
          files: 'Files',
          noWorkspace: 'No workspace',
          preview: 'Preview',
          selectTextFile: 'Select a text file',
          openFirst: 'Open a local project folder first.',
          noFiles: 'No files'
        },
        models: {
          matrix: 'Agent Model Matrix',
          matrixSubtitle: 'Agent model routes',
          editor: 'Route Editor',
          provider: 'Provider',
          model: 'Model',
          apiKeyEnv: 'API Key Environment Variable',
          baseUrl: 'Base URL',
          callsEnabled: 'Mark as real-call capable',
          hint: 'Only the environment variable name is saved, never the real API key. The current gateway still returns simulated responses.',
          ready: 'ready',
          simulated: 'simulated',
          present: 'present',
          missing: 'missing'
        },
        logs: {
          title: 'Trace Event Stream',
          noEvents: 'No events yet'
        },
        architecture: {
          layers: [
            ['Access Layer', 'Web Console, CLI, GitHub Webhook, REST API', 'implemented: Web + REST + webhook stub'],
            ['Core Services', 'api-service, workflow-service, agent-runtime, tool-executor', 'implemented: FastAPI + in-memory workflow/runtime'],
            ['Data Layer', 'PostgreSQL, Redis, MinIO, OpenSearch, pgvector', 'MVP: in-memory store, artifact records'],
            ['Model Layer', 'Model Gateway, provider routing, per-agent API key env', 'implemented: simulated gateway + route editor'],
            ['Execution Layer', 'isolated workspace, task branch, tool policy', 'MVP: local workspace + policy checks'],
            ['Observability', 'trace, audit logs, model/tool/chat events', 'implemented: event stream and trace endpoint']
          ]
        },
        settings: {
          languageTitle: 'Language',
          languageSubtitle: 'System interface language',
          languageLabel: 'Interface Language',
          languageHint: 'Language is saved in this browser and persists after refresh.',
          policy: 'Policy',
          policySubtitle: 'Approval and security policy',
          planApproval: 'Plan Approval',
          planApprovalText: 'manual_plan pauses for human approval after Planning by default.',
          secretGuard: 'Secret Guard',
          secretGuardText: 'Model config rejects likely real API keys and only accepts environment variable names.',
          sandboxMode: 'Sandbox Mode',
          sandboxModeText: 'Tool calls are audited through SecurityPolicy and ToolExecutor.',
          health: 'Integration Health',
          healthSubtitle: 'Runtime status',
          adapterConfigured: 'adapter configured',
          simulated: 'simulated'
        },
        toast: {
          taskCanceled: 'Task canceled',
          finderOpened: 'Project opened in Finder',
          revealUnsupported: 'Opening folders is not supported on this system',
          pickerCanceled: 'Project folder selection canceled',
          pickerUnsupported: 'Folder picker is not supported on this system',
          healthComplete: 'Health check complete',
          taskCreated: 'Task created',
          workspaceOpened: 'Local project opened',
          modelSaved: 'Model route saved',
          selectTaskFirst: 'Select a task first',
          agentReplied: 'Agent replied'
        }
      }
    };
    const VIEW_META = {
      overview: 'overview',
      tasks: 'tasks',
      agents: 'agents',
      workspace: 'workspace',
      models: 'models',
      logs: 'logs',
      architecture: 'architecture',
      settings: 'settings'
    };

    function initialLanguage() {
      try {
        return localStorage.getItem(LANGUAGE_STORAGE_KEY) === 'en' ? 'en' : 'zh';
      } catch (_) {
        return 'zh';
      }
    }

    const state = {
      view: 'overview',
      language: initialLanguage(),
      selectedTaskId: null,
      selectedAgent: 'orchestrator',
      selectedModelAgent: 'orchestrator',
      workspace: null,
      workspaceFiles: [],
      workspaceDir: '',
      filePreview: null,
      tasks: [],
      taskView: null,
      trace: null,
      messages: [],
      statuses: [],
      models: [],
      eventFilter: 'all',
      health: null
    };

    async function api(path, options = {}) {
      const init = { ...options, headers: { 'Content-Type': 'application/json', ...(options.headers || {}) } };
      const response = await fetch(path, init);
      if (!response.ok) {
        let detail = response.statusText;
        try {
          const payload = await response.json();
          detail = payload.detail || detail;
        } catch (_) {}
        throw new Error(detail);
      }
      if (response.status === 204) return null;
      return response.json();
    }

    function escapeHtml(value) {
      return String(value ?? '').replace(/[&<>"']/g, char => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;'
      }[char]));
    }

    function showToast(message) {
      const toast = document.getElementById('toast');
      toast.textContent = message;
      toast.classList.add('show');
      clearTimeout(showToast.timer);
      showToast.timer = setTimeout(() => toast.classList.remove('show'), 2600);
    }

    function copy() {
      return COPY[state.language] || COPY.zh;
    }

    function copyPath(path) {
      return path.split('.').reduce((value, key) => value?.[key], copy());
    }

    function viewCopy(view) {
      return copy().views[VIEW_META[view] || 'overview'] || copy().views.overview;
    }

    function syncStaticCopy() {
      const t = copy();
      document.documentElement.lang = t.htmlLang;
      document.documentElement.dataset.language = state.language;
      document.querySelector('nav')?.setAttribute('aria-label', t.navAria);
      document.querySelectorAll('[data-copy-key]').forEach(element => {
        const value = copyPath(element.dataset.copyKey);
        if (typeof value === 'string') element.textContent = value;
      });
    }

    function agentMeta(agentName) {
      return AGENTS[agentName] || { label: agentName, role: 'Agent', mark: agentName?.[0]?.toUpperCase() || 'A', accent: '#91a2ba', x: '50%', y: '50%' };
    }

    function modelFor(agentName) {
      return state.models.find(item => item.agent_name === agentName) || {};
    }

    function statusFor(agentName) {
      return state.statuses.find(item => item.agent_name === agentName) || { agent_name: agentName, status: 'idle', ...modelFor(agentName) };
    }

    function progressFor(status, agentName) {
      const base = { completed: 92, running: 70, awaiting_approval: 58, failed: 28, pending: 22, idle: 12 }[status] ?? 14;
      return Math.min(98, base + AGENT_ORDER.indexOf(agentName) * 2);
    }

    function statusText(status) {
      const zhStatus = {
        idle: '空闲',
        pending: '等待中',
        running: '运行中',
        completed: '已完成',
        failed: '失败',
        canceled: '已取消',
        awaiting_approval: '待审批'
      };
      return state.language === 'zh' && zhStatus[status] ? zhStatus[status] : String(status || 'idle').replaceAll('_', ' ');
    }

    function shortId(value) {
      if (!value) return 'none';
      const text = String(value);
      return text.length > 18 ? `${text.slice(0, 8)}...${text.slice(-6)}` : text;
    }

    function formatTime(value) {
      if (!value) return '--:--:--';
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return '--:--:--';
      return date.toLocaleTimeString('zh-CN', { hour12: false });
    }

    function activeTask() {
      return state.taskView?.task || state.tasks.find(task => task.id === state.selectedTaskId) || state.tasks[0] || null;
    }

    function counts() {
      const byStatus = state.tasks.reduce((memo, task) => {
        memo[task.status] = (memo[task.status] || 0) + 1;
        return memo;
      }, {});
      const approvals = (state.taskView?.approvals || []).filter(item => item.status === 'awaiting_approval').length;
      return {
        total: state.tasks.length,
        running: (byStatus.running || 0) + (byStatus.created || 0),
        approval: byStatus.awaiting_approval || approvals,
        completed: byStatus.completed || 0,
        failed: (byStatus.failed || 0) + (byStatus.canceled || 0)
      };
    }

    function renderAll() {
      renderTop();
      renderNav();
      renderOverview();
      renderTasks();
      renderAgents();
      renderWorkspace();
      renderModels();
      renderLogs();
      renderArchitecture();
      renderSettings();
    }

    function renderTop() {
      const t = copy();
      const meta = viewCopy(state.view);
      const c = counts();
      syncStaticCopy();
      document.getElementById('viewTitle').textContent = meta[0];
      document.getElementById('viewSubtitle').textContent = meta[1];
      document.getElementById('topRunState').textContent = c.running || c.approval ? t.top.running : t.top.ready;
      document.getElementById('topTaskCount').textContent = c.total;
      document.getElementById('topApprovalCount').textContent = c.approval;
      const topModel = modelFor(state.selectedAgent);
      document.getElementById('topModelName').textContent = topModel.model ? `${topModel.provider}/${topModel.model}` : t.top.notConfigured;
      document.querySelectorAll('.view').forEach(view => view.classList.toggle('active', view.id === `view-${state.view}`));
      syncThemeToggle();
    }

    function renderNav() {
      const t = copy();
      document.querySelectorAll('.nav-button').forEach(button => {
        const meta = viewCopy(button.dataset.view);
        button.querySelector('span').textContent = meta[0];
        button.setAttribute('aria-label', `${meta[0]}${state.language === 'zh' ? '' : ' '}${t.moduleSuffix}`);
        button.classList.toggle('active', button.dataset.view === state.view);
      });
    }

    function renderOverview() {
      const task = activeTask();
      const c = counts();
      const t = copy();
      document.getElementById('view-overview').innerHTML = `
        <div class="grid">
          <div class="grid four">
            ${statCard(t.overview.totalTasks, c.total, t.overview.totalTasks)}
            ${statCard(t.overview.running, c.running, t.overview.running)}
            ${statCard(t.overview.awaitingApproval, c.approval, t.overview.awaitingApproval)}
            ${statCard(t.overview.completed, c.completed, t.overview.completed)}
          </div>
          <div class="grid two">
            <section class="panel">
              <div class="panel-head">
                <div><div class="panel-title">${t.overview.workflowCanvas}</div><div class="panel-subtitle">${t.overview.workflowSubtitle}</div></div>
                <div class="toolbar">
                  <button class="ghost" data-view-jump="tasks">${t.actions.openTask}</button>
                  <button class="primary" data-action="approve-first">${t.actions.approve}</button>
                </div>
              </div>
              <div class="panel-body">${workflowCanvas()}</div>
            </section>
            <section class="panel">
              <div class="panel-head">
                <div><div class="panel-title">${t.overview.currentTask}</div><div class="panel-subtitle">${task ? escapeHtml(task.current_step) : t.overview.noActiveTask}</div></div>
                <button class="ghost" data-view-jump="logs">${t.actions.trace}</button>
              </div>
              <div class="panel-body">
                ${task ? taskSummary(task) : `<div class="empty">${t.overview.noTask}</div>`}
              </div>
            </section>
          </div>
          <section class="panel">
            <div class="panel-head">
              <div><div class="panel-title">${t.overview.recentOutput}</div><div class="panel-subtitle">${t.overview.outputSubtitle}</div></div>
              <button class="ghost" data-view-jump="logs">${t.actions.viewAll}</button>
            </div>
            <div class="panel-body"><div class="event-list mono">${eventRows(12)}</div></div>
          </section>
        </div>
      `;
    }

    function statCard(label, value, sub) {
      return `<div class="stat"><span>${label}</span><strong>${value}</strong><small class="panel-subtitle">${sub}</small></div>`;
    }

    function taskSummary(task) {
      const approvals = (state.taskView?.approvals || []).filter(item => item.status === 'awaiting_approval');
      const t = copy();
      return `
        <div class="list">
          <div class="item">
            <div class="item-row"><strong class="item-title">${escapeHtml(task.prompt)}</strong><span class="tag">${task.status}</span></div>
            <div class="item-meta">Repo ${escapeHtml(task.repo_id)} · Branch ${escapeHtml(task.base_branch)} · ${escapeHtml(shortId(task.trace_id))}</div>
            <div class="item-meta">${escapeHtml(task.workspace_path || t.tasks.noWorkspaceBound)}</div>
          </div>
          ${approvals.map(item => approvalBox(task, item)).join('') || `<div class="empty">${t.tasks.noPendingApproval}</div>`}
        </div>
      `;
    }

    function workflowCanvas() {
      const task = activeTask();
      return `
        <div class="flow-canvas">
          <svg class="flow-line" viewBox="0 0 1000 520" preserveAspectRatio="none">
            <path d="M500 94 C500 150 290 164 210 224" />
            <path d="M500 94 C500 150 710 164 790 224" />
            <path d="M210 224 C310 250 405 250 500 224" />
            <path d="M500 224 C595 250 690 250 790 224" />
            <path d="M500 254 C438 324 385 344 350 354" />
            <path d="M500 254 C570 316 622 336 650 354" />
            <path d="M350 354 C420 438 488 438 500 406" />
            <path d="M650 354 C700 400 760 400 820 394" />
            <path d="M500 406 C610 456 730 446 820 394" />
          </svg>
          <div class="tag" style="position:absolute;left:14px;top:14px;">${task ? escapeHtml(shortId(task.trace_id)) : 'TRACE WAIT'}</div>
          ${AGENT_ORDER.map(agent => flowNode(agent)).join('')}
        </div>
      `;
    }

    function flowNode(agentName) {
      const meta = agentMeta(agentName);
      const status = statusFor(agentName);
      const progress = progressFor(status.status, agentName);
      return `
        <button class="flow-card ${state.selectedAgent === agentName ? 'selected' : ''}" data-agent="${agentName}" style="--x:${meta.x};--y:${meta.y};--accent:${meta.accent};">
          <span class="mark">${meta.mark}</span>
          <span class="flow-main"><strong>${meta.label}</strong><span>${meta.role} · ${statusText(status.status)}</span></span>
          <span class="ring" style="--progress:${progress}%">${progress}%</span>
        </button>
      `;
    }

    function renderTasks() {
      const t = copy();
      document.getElementById('view-tasks').innerHTML = `
        <div class="grid board">
          <section class="panel">
            <div class="panel-head">
              <div><div class="panel-title">${t.tasks.createTitle}</div><div class="panel-subtitle">${t.tasks.createSubtitle}</div></div>
            </div>
            <div class="panel-body">
              <form class="form" id="taskForm">
                <label>${t.tasks.repoId} <input name="repo_id" value="local/agentsystem" required></label>
                <label>${t.tasks.prompt} <textarea name="prompt" required placeholder="${t.tasks.promptPlaceholder}">${t.tasks.promptDefault}</textarea></label>
                <div class="form-row">
                  <label>${t.tasks.baseBranch} <input name="base_branch" value="main" required></label>
                  <label>${t.tasks.priority}
                    <select name="priority"><option value="normal">normal</option><option value="high">high</option><option value="low">low</option></select>
                  </label>
                </div>
                <label>${t.tasks.approvalPolicy}
                  <select name="approval_policy"><option value="manual_plan">manual_plan</option><option value="manual_all">manual_all</option><option value="auto">auto</option></select>
                </label>
                <button class="primary" type="submit">${t.tasks.launch}</button>
              </form>
            </div>
          </section>
          <section class="panel">
            <div class="panel-head">
              <div><div class="panel-title">${t.tasks.boardTitle}</div><div class="panel-subtitle">${t.tasks.boardSubtitle}</div></div>
              <button class="ghost" data-action="reload">${t.actions.reload}</button>
            </div>
            <div class="panel-body"><div class="task-board">${taskBoard()}</div></div>
          </section>
          <section class="panel" style="grid-column: 1 / -1;">
            <div class="panel-head">
              <div><div class="panel-title">${t.tasks.detailTitle}</div><div class="panel-subtitle">${state.selectedTaskId ? shortId(state.selectedTaskId) : t.tasks.noTaskSelected}</div></div>
              <div class="toolbar"><button class="danger" data-action="cancel-task" ${state.selectedTaskId ? '' : 'disabled'}>${t.actions.cancel}</button><button class="ghost" data-view-jump="logs">${t.actions.trace}</button></div>
            </div>
            <div class="panel-body">${taskDetail()}</div>
          </section>
        </div>
      `;
    }

    function taskBoard() {
      const t = copy();
      const groups = [
        ['created', t.taskColumns.created, ['created']],
        ['running', t.taskColumns.running, ['running']],
        ['awaiting_approval', t.taskColumns.approval, ['awaiting_approval']],
        ['completed', t.taskColumns.done, ['completed']],
        ['stopped', t.taskColumns.stopped, ['failed', 'canceled']]
      ];
      return groups.map(([status, label, statuses]) => `
        <div class="column">
          <h3>${label}</h3>
          ${state.tasks.filter(task => statuses.includes(task.status)).map(task => taskCard(task)).join('') || `<div class="empty">${t.tasks.emptyColumn}</div>`}
        </div>
      `).join('');
    }

    function taskCard(task) {
      return `
        <button class="item ${task.id === state.selectedTaskId ? 'selected' : ''}" data-task="${task.id}" data-action="select-task">
          <span class="item-title">${escapeHtml(task.prompt)}</span>
          <span class="item-meta">${escapeHtml(task.current_step)} · ${escapeHtml(task.priority)}</span>
          <span class="item-meta">${escapeHtml(task.repo_id)}</span>
        </button>
      `;
    }

    function taskDetail() {
      const task = activeTask();
      const t = copy();
      if (!task) return `<div class="empty">${t.tasks.selectOrCreate}</div>`;
      const approvals = state.taskView?.approvals || [];
      const artifacts = state.taskView?.artifacts || [];
      return `
        <div class="grid two">
          <div class="grid">
            ${taskSummary(task)}
            <section class="panel">
              <div class="panel-head"><div><div class="panel-title">${t.tasks.artifacts}</div><div class="panel-subtitle">${t.tasks.artifactsSubtitle}</div></div></div>
              <div class="panel-body artifact-list list">${artifacts.map(artifactCard).join('') || `<div class="empty">${t.tasks.noArtifacts}</div>`}</div>
            </section>
          </div>
          <section class="panel">
            <div class="panel-head"><div><div class="panel-title">${t.tasks.aiCollaboration}</div><div class="panel-subtitle">${t.tasks.aiSubtitle}</div></div></div>
            <div class="panel-body">
              <div class="chat-log list">${chatMessages()}</div>
              <form class="form" id="chatForm">
                <textarea name="content" required placeholder="${t.tasks.chatPlaceholder}"></textarea>
                <div class="form-row">
                  <select name="agent_name">${AGENT_ORDER.map(name => `<option value="${name}" ${name === state.selectedAgent ? 'selected' : ''}>${agentMeta(name).label}</option>`).join('')}</select>
                  <button class="primary" type="submit">${t.actions.send}</button>
                </div>
              </form>
            </div>
          </section>
        </div>
      `;
    }

    function approvalBox(task, approval) {
      return `
        <div class="item approval">
          <div class="item-row"><strong>${approval.approval_type}</strong><span class="tag">${approval.status}</span></div>
          <div class="item-meta">${escapeHtml(approval.reason)}</div>
          <div class="toolbar">
            <button class="primary" data-action="approve" data-task="${task.id}" data-approval="${approval.id}">通过</button>
            <button class="danger" data-action="reject" data-task="${task.id}" data-approval="${approval.id}">拒绝</button>
          </div>
        </div>
      `;
    }

    function artifactCard(artifact) {
      return `<div class="item"><div class="item-row"><strong>${escapeHtml(artifact.kind)}</strong><span class="tag">${formatTime(artifact.created_at)}</span></div><div class="item-meta">${escapeHtml(artifact.name)}</div><pre class="preview">${escapeHtml(artifact.content)}</pre></div>`;
    }

    function chatMessages() {
      return state.messages.length ? state.messages.map(message => `
        <div class="message ${message.role}">
          <div class="item-meta">${escapeHtml(message.role)} · ${escapeHtml(message.agent_name || 'system')} · ${formatTime(message.created_at)}</div>
          ${escapeHtml(message.content)}
        </div>
      `).join('') : '<div class="empty">暂无对话消息</div>';
    }

    function renderAgents() {
      const t = copy();
      document.getElementById('view-agents').innerHTML = `
        <div class="grid split">
          <section class="panel">
            <div class="panel-head"><div><div class="panel-title">${t.agents.roster}</div><div class="panel-subtitle">${t.agents.rosterSubtitle}</div></div></div>
            <div class="panel-body list">${AGENT_ORDER.map(agentRosterCard).join('')}</div>
          </section>
          <section class="panel">
            <div class="panel-head"><div><div class="panel-title">${t.agents.inspector}</div><div class="panel-subtitle">${agentMeta(state.selectedAgent).label}</div></div><button class="ghost" data-view-jump="models">${t.actions.configureModel}</button></div>
            <div class="panel-body">${agentInspector()}</div>
          </section>
        </div>
      `;
    }

    function agentRosterCard(agentName) {
      const meta = agentMeta(agentName);
      const status = statusFor(agentName);
      const model = modelFor(agentName);
      const progress = progressFor(status.status, agentName);
      return `
        <button class="item ${agentName === state.selectedAgent ? 'selected' : ''}" data-agent="${agentName}">
          <div class="item-row">
            <span class="toolbar"><span class="mark" style="--accent:${meta.accent}">${meta.mark}</span><span><strong class="item-title">${meta.label}</strong><span class="item-meta">${meta.role} · ${statusText(status.status)}</span></span></span>
            <span class="ring" style="--progress:${progress}%">${progress}%</span>
          </div>
          <span class="item-meta">${escapeHtml(model.provider || '-')} / ${escapeHtml(model.model || '-')}</span>
        </button>
      `;
    }

    function agentInspector() {
      const status = statusFor(state.selectedAgent);
      const model = modelFor(state.selectedAgent);
      const t = copy();
      return `
        <div class="grid">
          <div class="grid three">
            ${statCard(t.agents.status, statusText(status.status), t.agents.currentStatus)}
            ${statCard(t.agents.latency, status.latency_ms ? `${status.latency_ms}ms` : t.agents.simulated, t.agents.lastRun)}
            ${statCard(t.agents.handoff, status.handoff_to || '-', t.agents.nextAgent)}
          </div>
          <div class="item">
            <strong>${t.agents.objective}</strong>
            <span class="item-meta">${escapeHtml(status.last_summary || defaultObjective(state.selectedAgent))}</span>
          </div>
          <div class="item">
            <strong>${t.agents.modelProfile}</strong>
            <span class="item-meta">${escapeHtml(model.provider || '-')} / ${escapeHtml(model.model || '-')}</span>
            <span class="item-meta">${escapeHtml(model.api_key_env || '-')} · ${model.api_key_present ? t.agents.present : t.agents.missing} · ${model.calls_enabled ? t.agents.enabled : t.agents.simulated}</span>
          </div>
          <section class="panel">
            <div class="panel-head"><div><div class="panel-title">${t.agents.events}</div><div class="panel-subtitle">${agentMeta(state.selectedAgent).label}</div></div></div>
            <div class="panel-body"><div class="event-list mono">${eventRows(18, state.selectedAgent)}</div></div>
          </section>
        </div>
      `;
    }

    function defaultObjective(agentName) {
      return {
        orchestrator: '识别任务类型、拆分步骤、控制预算并触发审批。',
        repo_context: '打开本地项目，检索相关文件，生成代码上下文包。',
        planning: '输出实现计划、风险和测试策略。',
        coding: '根据计划生成最小补丁。',
        test: '运行 lint、typecheck、unit/integration tests 并解释失败。',
        security: '执行 secret scan、越权访问和 prompt injection 检查。',
        review: '审查功能正确性、回归风险、风格和测试缺口。',
        pr: '创建 draft PR 并附带方案、摘要、测试结果和 trace。'
      }[agentName] || '等待任务调度。';
    }

    function renderWorkspace() {
      const t = copy();
      document.getElementById('view-workspace').innerHTML = `
        <div class="grid">
          <section class="panel">
            <div class="panel-head"><div><div class="panel-title">${t.workspace.title}</div><div class="panel-subtitle">${t.actions.localProject}</div></div></div>
            <div class="panel-body">
              <div class="form" id="workspaceControls">
                <div class="form-row">
                  <div class="path-display" role="status" aria-live="polite">
                    <strong>${t.workspace.selectedProjectPath}</strong>
                    <code>${escapeHtml(state.workspace?.path || DEFAULT_WORKSPACE)}</code>
                  </div>
                  <label>${t.workspace.currentDir} <input value="${escapeHtml(state.workspaceDir || '/')}" readonly></label>
                </div>
                <div class="toolbar">
                  <button class="primary" type="button" data-action="pick-workspace">${t.actions.selectProjectFolder}</button>
                  <button class="ghost" type="button" data-action="workspace-root">${t.actions.root}</button>
                  <button class="ghost" type="button" data-action="reveal-workspace" ${state.workspace ? '' : 'disabled'}>${t.actions.showInFinder}</button>
                </div>
              </div>
            </div>
          </section>
          <div class="file-browser">
            <section class="panel">
              <div class="panel-head"><div><div class="panel-title">${t.workspace.files}</div><div class="panel-subtitle">${escapeHtml(state.workspace?.summary?.split('\\n')[0] || t.workspace.noWorkspace)}</div></div></div>
              <div class="panel-body"><div class="file-list list">${workspaceFileRows()}</div></div>
            </section>
            <section class="panel">
              <div class="panel-head"><div><div class="panel-title">${t.workspace.preview}</div><div class="panel-subtitle">${escapeHtml(state.filePreview?.path || t.workspace.selectTextFile)}</div></div><button class="ghost" data-action="task-from-workspace">${t.actions.taskFromWorkspace}</button></div>
              <div class="panel-body">${filePreview()}</div>
            </section>
          </div>
        </div>
      `;
    }

    function workspaceFileRows() {
      const t = copy();
      if (!state.workspace) return `<div class="empty">${t.workspace.openFirst}</div>`;
      const parent = state.workspaceDir ? state.workspaceDir.split('/').slice(0, -1).join('/') : '';
      const up = state.workspaceDir ? `<button class="item file-button" data-dir="${escapeHtml(parent)}" data-action="open-dir"><span>dir</span><strong>..</strong><span></span></button>` : '';
      return up + (state.workspaceFiles.map(file => `
        <button class="item file-button" data-action="${file.kind === 'directory' ? 'open-dir' : 'preview-file'}" data-path="${escapeHtml(file.path)}" data-dir="${escapeHtml(file.path)}">
          <span>${file.kind === 'directory' ? 'dir' : 'file'}</span>
          <strong class="truncate">${escapeHtml(file.name)}</strong>
          <span class="item-meta">${file.size_bytes ?? ''}</span>
        </button>
      `).join('') || `<div class="empty">${t.workspace.noFiles}</div>`);
    }

    function filePreview() {
      if (!state.filePreview) return '<div class="empty">选择 `.py`、`.md`、`.json`、`.ts` 等文本文件后预览。</div>';
      return `<pre class="preview">${escapeHtml(state.filePreview.content)}${state.filePreview.truncated ? '\\n\\n[truncated]' : ''}</pre>`;
    }

    function renderModels() {
      const selected = modelFor(state.selectedModelAgent);
      const t = copy();
      document.getElementById('view-models').innerHTML = `
        <div class="grid two">
          <section class="panel">
            <div class="panel-head"><div><div class="panel-title">${t.models.matrix}</div><div class="panel-subtitle">${t.models.matrixSubtitle}</div></div></div>
            <div class="panel-body"><div class="model-grid">${AGENT_ORDER.map(modelCard).join('')}</div></div>
          </section>
          <section class="panel">
            <div class="panel-head"><div><div class="panel-title">${t.models.editor}</div><div class="panel-subtitle">${agentMeta(state.selectedModelAgent).label}</div></div></div>
            <div class="panel-body">
              <form class="form" id="modelForm">
                <input type="hidden" name="agent_name" value="${escapeHtml(state.selectedModelAgent)}">
                <div class="form-row">
                  <label>${t.models.provider} <input name="provider" value="${escapeHtml(selected.provider || '')}" required></label>
                  <label>${t.models.model} <input name="model" value="${escapeHtml(selected.model || '')}" required></label>
                </div>
                <label>${t.models.apiKeyEnv} <input name="api_key_env" value="${escapeHtml(selected.api_key_env || '')}" required placeholder="CODING_AGENT_API_KEY"></label>
                <label>${t.models.baseUrl} <input name="base_url" value="${escapeHtml(selected.base_url || '')}" placeholder="http://model-gateway.internal/v1"></label>
                <label><span class="toolbar"><input type="checkbox" name="calls_enabled" style="width:auto;min-height:auto;" ${selected.calls_enabled ? 'checked' : ''}> ${t.models.callsEnabled}</span></label>
                <div class="item-meta">${t.models.hint}</div>
                <button class="primary" type="submit">${t.actions.saveAgentRoute}</button>
              </form>
            </div>
          </section>
        </div>
      `;
    }

    function modelCard(agentName) {
      const model = modelFor(agentName);
      const t = copy();
      return `
        <button class="item ${state.selectedModelAgent === agentName ? 'selected' : ''}" data-model-agent="${agentName}">
          <div class="item-row"><strong>${agentMeta(agentName).label}</strong><span class="tag">${model.calls_enabled ? t.models.ready : t.models.simulated}</span></div>
          <span class="item-meta">${escapeHtml(model.provider || '-')} / ${escapeHtml(model.model || '-')}</span>
          <span class="item-meta">${escapeHtml(model.api_key_env || '-')} · ${model.api_key_present ? t.models.present : t.models.missing}</span>
        </button>
      `;
    }

    function renderLogs() {
      const t = copy();
      document.getElementById('view-logs').innerHTML = `
        <section class="panel">
          <div class="panel-head">
            <div><div class="panel-title">${t.logs.title}</div><div class="panel-subtitle">${viewCopy('logs')[1]}</div></div>
            <div class="toolbar">
              ${['all', 'agent', 'model', 'tool', 'chat', 'system'].map(filter => `<button class="${state.eventFilter === filter ? 'primary' : 'ghost'}" data-filter="${filter}">${filter}</button>`).join('')}
            </div>
          </div>
          <div class="panel-body"><div class="event-list mono">${eventRows(120)}</div></div>
        </section>
      `;
    }

    function collectEvents() {
      const trace = state.trace || {};
      const rows = [];
      (trace.events || []).forEach(item => rows.push({ time: item.created_at, category: item.event_type?.startsWith('agent') ? 'agent' : 'system', actor: item.actor, type: item.event_type, body: eventText(item.payload) }));
      (trace.agent_runs || []).forEach(item => rows.push({ time: item.completed_at || item.started_at, category: 'agent', actor: item.agent_name, type: item.output_summary ? 'agent.completed' : 'agent.started', body: item.output_summary || item.input_summary || '' }));
      (trace.model_calls || []).forEach(item => rows.push({ time: item.created_at, category: 'model', actor: item.agent_name, type: 'model.call', body: `${item.provider}/${item.model} | ${item.api_key_env}: ${item.api_key_present ? 'present' : 'missing'} | ${item.simulated ? 'simulated' : 'enabled'}` }));
      (trace.tool_calls || []).forEach(item => rows.push({ time: item.created_at, category: 'tool', actor: item.agent_name, type: `tool.${item.tool_name}`, body: `${item.allowed ? 'allowed' : 'blocked'} | ${item.output_summary || item.input_summary || ''}` }));
      (trace.audit_logs || []).forEach(item => rows.push({ time: item.created_at, category: 'system', actor: item.actor, type: item.action, body: eventText(item.details) }));
      (trace.chat_messages || []).forEach(item => rows.push({ time: item.created_at, category: 'chat', actor: item.agent_name || item.role, type: `chat.${item.role}`, body: item.content }));
      if (!rows.length) {
        state.models.forEach(item => rows.push({ time: new Date().toISOString(), category: 'model', actor: item.agent_name, type: 'model.route', body: `${item.provider}/${item.model} | ${item.api_key_env}: ${item.api_key_present ? 'present' : 'missing'} | simulated` }));
      }
      return rows.sort((a, b) => new Date(a.time || 0) - new Date(b.time || 0));
    }

    function eventText(payload) {
      if (!payload) return '';
      if (typeof payload === 'string') return payload;
      if (payload.summary) return payload.summary;
      if (payload.reason) return payload.reason;
      const text = JSON.stringify(payload);
      return text.length > 240 ? `${text.slice(0, 240)}...` : text;
    }

    function eventRows(limit, actor = null) {
      const t = copy();
      const rows = collectEvents().filter(item => {
        const categoryOk = state.eventFilter === 'all' || item.category === state.eventFilter;
        const actorOk = !actor || item.actor === actor;
        return categoryOk && actorOk;
      }).slice(-limit);
      return rows.length ? rows.map(item => `
        <div class="event-row">
          <span class="event-time">${formatTime(item.time)}</span>
          <span class="event-actor">${escapeHtml(item.actor)}</span>
          <span class="event-type">${escapeHtml(item.type)}</span>
          <span class="event-body">${escapeHtml(item.body)}</span>
        </div>
      `).join('') : `<div class="empty">${t.logs.noEvents}</div>`;
    }

    function renderArchitecture() {
      const layers = copy().architecture.layers;
      document.getElementById('view-architecture').innerHTML = `
        <div class="arch-grid">
          ${layers.map(([title, body, status]) => `<div class="panel"><div class="panel-head"><div><div class="panel-title">${title}</div><div class="panel-subtitle">${body}</div></div></div><div class="panel-body"><div class="item"><span class="status-dot ok"></span><span>${status}</span></div></div></div>`).join('')}
        </div>
      `;
    }

    function renderSettings() {
      const t = copy();
      document.getElementById('view-settings').innerHTML = `
        <div class="grid two">
          <section class="panel">
            <div class="panel-head"><div><div class="panel-title">${t.settings.languageTitle}</div><div class="panel-subtitle">${t.settings.languageSubtitle}</div></div></div>
            <div class="panel-body list">
              <label for="languageSelect">${t.settings.languageLabel}
                <select id="languageSelect" name="language">
                  <option value="zh" ${state.language === 'zh' ? 'selected' : ''}>${t.language.zh}</option>
                  <option value="en" ${state.language === 'en' ? 'selected' : ''}>${t.language.en}</option>
                </select>
              </label>
              <div class="item-meta">${t.settings.languageHint}</div>
            </div>
          </section>
          <section class="panel">
            <div class="panel-head"><div><div class="panel-title">${t.settings.policy}</div><div class="panel-subtitle">${t.settings.policySubtitle}</div></div></div>
            <div class="panel-body list">
              <div class="item"><strong>${t.settings.planApproval}</strong><span class="item-meta">${t.settings.planApprovalText}</span></div>
              <div class="item"><strong>${t.settings.secretGuard}</strong><span class="item-meta">${t.settings.secretGuardText}</span></div>
              <div class="item"><strong>${t.settings.sandboxMode}</strong><span class="item-meta">${t.settings.sandboxModeText}</span></div>
            </div>
          </section>
          <section class="panel">
            <div class="panel-head"><div><div class="panel-title">${t.settings.health}</div><div class="panel-subtitle">${t.settings.healthSubtitle}</div></div><button class="ghost" data-action="health">${t.actions.check}</button></div>
            <div class="panel-body list">
              <div class="item"><div class="item-row"><strong>API</strong><span class="tag">${state.health?.status || 'unknown'}</span></div></div>
              <div class="item"><div class="item-row"><strong>GitHub Enterprise</strong><span class="tag">${t.settings.adapterConfigured}</span></div></div>
              <div class="item"><div class="item-row"><strong>Model Gateway</strong><span class="tag">${t.settings.simulated}</span></div></div>
            </div>
          </section>
        </div>
      `;
    }

    async function loadModels() {
      state.models = await api('/agent-models');
    }

    async function loadStatuses() {
      const suffix = state.selectedTaskId ? `?task_id=${encodeURIComponent(state.selectedTaskId)}` : '';
      state.statuses = await api(`/agent-status${suffix}`);
    }

    async function loadTasks() {
      state.tasks = await api('/tasks');
      if (!state.selectedTaskId && state.tasks.length) {
        await loadTaskDetail(state.tasks[0].id);
      } else if (state.selectedTaskId) {
        const stillExists = state.tasks.some(task => task.id === state.selectedTaskId);
        if (stillExists) await loadTaskDetail(state.selectedTaskId);
      }
    }

    async function loadTaskDetail(taskId) {
      state.selectedTaskId = taskId;
      state.taskView = await api(`/tasks/${taskId}`);
      state.trace = await api(`/tasks/${taskId}/trace`);
      state.messages = await api(`/tasks/${taskId}/messages`);
      await loadStatuses();
    }

    async function openWorkspace(path, dir = '') {
      state.workspace = await api('/workspaces/open', { method: 'POST', body: JSON.stringify({ path }) });
      state.workspaceDir = dir;
      state.workspaceFiles = await api(`/workspaces/${state.workspace.id}/files?path=${encodeURIComponent(dir)}`);
      state.filePreview = null;
    }

    async function refreshAll() {
      await loadModels();
      await loadTasks();
      await loadStatuses();
      if (state.workspace) {
        state.workspaceFiles = await api(`/workspaces/${state.workspace.id}/files?path=${encodeURIComponent(state.workspaceDir)}`);
      }
      renderAll();
    }

    async function approveFirst(approved = true) {
      const task = activeTask();
      const approval = (state.taskView?.approvals || []).find(item => item.status === 'awaiting_approval');
      if (!task || !approval) {
        showToast('当前没有待审批项');
        return;
      }
      await api(`/tasks/${task.id}/approve`, {
        method: 'POST',
        body: JSON.stringify({
          approval_id: approval.id,
          approved,
          actor: 'console',
          comment: approved ? 'Approved in console' : 'Rejected in console'
        })
      });
      await refreshAll();
      showToast(approved ? '审批已通过' : '审批已拒绝');
    }

    function currentTheme() {
      return document.documentElement.dataset.theme === 'light' ? 'light' : 'dark';
    }

    function syncThemeToggle() {
      const button = document.getElementById('themeToggle');
      if (!button) return;
      const t = copy();
      const theme = currentTheme();
      const nextLabel = theme === 'light' ? t.theme.nightButton : t.theme.dayButton;
      button.textContent = nextLabel;
      button.setAttribute('aria-pressed', theme === 'light' ? 'true' : 'false');
      button.setAttribute('title', t.theme.title(nextLabel));
    }

    function setTheme(theme) {
      const normalized = theme === 'light' ? 'light' : 'dark';
      const t = copy();
      document.documentElement.dataset.theme = normalized;
      try {
        localStorage.setItem('agentsystem-theme', normalized);
      } catch (_) {}
      syncThemeToggle();
      showToast(t.theme.switched(normalized === 'light' ? t.theme.dayButton : t.theme.nightButton));
    }

    function setLanguage(language) {
      const normalized = language === 'en' ? 'en' : 'zh';
      state.language = normalized;
      try {
        localStorage.setItem(LANGUAGE_STORAGE_KEY, normalized);
      } catch (_) {}
      renderAll();
      showToast(normalized === 'zh' ? copy().language.switched : copy().language.switchedEn);
    }

    document.addEventListener('click', async event => {
      const t = copy();
      const nav = event.target.closest('[data-view], [data-view-jump]');
      if (nav) {
        state.view = nav.dataset.view || nav.dataset.viewJump;
        renderAll();
        return;
      }

      const agent = event.target.closest('[data-agent]');
      if (agent) {
        state.selectedAgent = agent.dataset.agent;
        state.selectedModelAgent = agent.dataset.agent;
        state.view = state.view === 'overview' ? 'agents' : state.view;
        renderAll();
        return;
      }

      const modelAgent = event.target.closest('[data-model-agent]');
      if (modelAgent) {
        state.selectedModelAgent = modelAgent.dataset.modelAgent;
        state.selectedAgent = modelAgent.dataset.modelAgent;
        renderAll();
        return;
      }

      const filter = event.target.closest('[data-filter]');
      if (filter) {
        state.eventFilter = filter.dataset.filter;
        renderAll();
        return;
      }

      const action = event.target.closest('[data-action]');
      if (!action) return;
      try {
        if (action.dataset.action === 'reload') await refreshAll();
        if (action.dataset.action === 'select-task') {
          await loadTaskDetail(action.dataset.task);
          renderAll();
        }
        if (action.dataset.action === 'approve' || action.dataset.action === 'reject') {
          await api(`/tasks/${action.dataset.task}/approve`, {
            method: 'POST',
            body: JSON.stringify({
              approval_id: action.dataset.approval,
              approved: action.dataset.action === 'approve',
              actor: 'console',
              comment: action.dataset.action === 'approve' ? 'Approved in console' : 'Rejected in console'
            })
          });
          await refreshAll();
          showToast(action.dataset.action === 'approve' ? '审批已通过' : '审批已拒绝');
        }
        if (action.dataset.action === 'approve-first') await approveFirst(true);
        if (action.dataset.action === 'cancel-task' && state.selectedTaskId) {
          await api(`/tasks/${state.selectedTaskId}/cancel`, { method: 'POST', body: '{}' });
          await refreshAll();
          showToast(t.toast.taskCanceled);
        }
        if (action.dataset.action === 'pick-workspace') {
          const result = await api('/workspaces/pick', { method: 'POST', body: '{}' });
          if (result.status === 'selected' && result.path) {
            await openWorkspace(result.path, '');
            renderAll();
            showToast(t.toast.workspaceOpened);
          } else {
            showToast(result.status === 'canceled' ? t.toast.pickerCanceled : t.toast.pickerUnsupported);
          }
        }
        if (action.dataset.action === 'open-dir') {
          await openWorkspace(state.workspace.path, action.dataset.dir || '');
          renderAll();
        }
        if (action.dataset.action === 'workspace-root') {
          await openWorkspace(state.workspace?.path || DEFAULT_WORKSPACE, '');
          renderAll();
        }
        if (action.dataset.action === 'reveal-workspace' && state.workspace) {
          const result = await api(`/workspaces/${state.workspace.id}/reveal`, { method: 'POST', body: '{}' });
          showToast(result.status === 'opened' ? t.toast.finderOpened : t.toast.revealUnsupported);
        }
        if (action.dataset.action === 'preview-file') {
          state.filePreview = await api(`/workspaces/${state.workspace.id}/file?path=${encodeURIComponent(action.dataset.path)}`);
          renderAll();
        }
        if (action.dataset.action === 'task-from-workspace') {
          state.view = 'tasks';
          renderAll();
          const taskForm = document.getElementById('taskForm');
          if (taskForm && state.workspace) {
            taskForm.elements.repo_id.value = `local/${state.workspace.name}`;
            taskForm.elements.prompt.value = `基于本地项目 ${state.workspace.path} 进行代码协同：请 Repo Context 定位相关文件，Planning 输出计划，Coding 准备补丁，Review/Security 做审查。`;
          }
          document.querySelector('#taskForm textarea')?.focus();
        }
        if (action.dataset.action === 'health') {
          state.health = await api('/health');
          renderAll();
          showToast(t.toast.healthComplete);
        }
      } catch (error) {
        showToast(error.message);
      }
    });

    document.addEventListener('change', event => {
      if (event.target.id === 'languageSelect') {
        setLanguage(event.target.value);
      }
    });

    document.addEventListener('submit', async event => {
      const t = copy();
      if (event.target.id === 'taskForm') {
        event.preventDefault();
        const form = new FormData(event.target);
        const payload = Object.fromEntries(form.entries());
        if (state.workspace?.path) payload.workspace_path = state.workspace.path;
        try {
          const view = await api('/tasks', { method: 'POST', body: JSON.stringify(payload) });
          await loadTaskDetail(view.task.id);
          await loadTasks();
          state.view = 'tasks';
          renderAll();
          showToast(t.toast.taskCreated);
        } catch (error) {
          showToast(error.message);
        }
      }

      if (event.target.id === 'modelForm') {
        event.preventDefault();
        const form = new FormData(event.target);
        const agentName = form.get('agent_name');
        const payload = {
          provider: form.get('provider'),
          model: form.get('model'),
          api_key_env: form.get('api_key_env'),
          base_url: form.get('base_url') || null,
          calls_enabled: form.get('calls_enabled') === 'on'
        };
        try {
          await api(`/agent-models/${agentName}`, { method: 'PUT', body: JSON.stringify(payload) });
          await loadModels();
          await loadStatuses();
          renderAll();
          showToast(t.toast.modelSaved);
        } catch (error) {
          showToast(error.message);
        }
      }

      if (event.target.id === 'chatForm') {
        event.preventDefault();
        if (!state.selectedTaskId) {
          showToast(t.toast.selectTaskFirst);
          return;
        }
        const form = new FormData(event.target);
        const payload = Object.fromEntries(form.entries());
        try {
          state.messages = await api(`/tasks/${state.selectedTaskId}/messages`, { method: 'POST', body: JSON.stringify(payload) });
          state.selectedAgent = payload.agent_name;
          await loadTaskDetail(state.selectedTaskId);
          event.target.reset();
          renderAll();
          showToast(t.toast.agentReplied);
        } catch (error) {
          showToast(error.message);
        }
      }
    });

    document.getElementById('refreshBtn').addEventListener('click', () => refreshAll().catch(error => showToast(error.message)));
    document.getElementById('themeToggle').addEventListener('click', () => {
      setTheme(currentTheme() === 'light' ? 'dark' : 'light');
    });
    syncThemeToggle();

    Promise.all([loadModels(), openWorkspace(DEFAULT_WORKSPACE)])
      .then(() => loadTasks())
      .then(() => loadStatuses())
      .then(renderAll)
      .catch(error => {
        showToast(error.message);
        renderAll();
      });
  </script>
</body>
</html>""".replace(
        "__DEFAULT_WORKSPACE_JSON__",
        json.dumps(default_workspace),
    ).replace(
        "__DEFAULT_WORKSPACE_VALUE__",
        escape(default_workspace, quote=True),
    )
