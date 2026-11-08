#!/usr/bin/env bash
# 启动 web 静态站（跑构建产物 out/，不是 next dev）
#
#   ./scripts/serve-web.sh start              # 没有产物就先构建，然后起在 8811
#   ./scripts/serve-web.sh start --build      # 强制重新构建
#   ./scripts/serve-web.sh start --port 8900  # 换端口
#   ./scripts/serve-web.sh start --tunnel     # 同时开一条 serveo 临时公网地址
#   ./scripts/serve-web.sh stop | status | logs | restart
#
# 环境变量：PORT（默认 8811）、BASE_PATH（子路径部署，如 /personal-album-platform）

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB="$ROOT/apps/web"
OUT="$WEB/out"
RUN="$ROOT/.run"
PID_FILE="$RUN/web.pid"
PORT_FILE="$RUN/web.port"
LOG_FILE="$RUN/web.log"
TUN_PID="$RUN/tunnel.pid"
TUN_LOG="$RUN/tunnel.log"
TUN_URL="$RUN/tunnel.url"

PORT="${PORT:-8811}"
BASE_PATH="${BASE_PATH:-}"

say()  { printf '\033[1m%s\033[0m\n' "$*"; }
warn() { printf '\033[33m%s\033[0m\n' "$*" >&2; }
die()  { printf '\033[31m%s\033[0m\n' "$*" >&2; exit 1; }

alive() { [[ -f "$1" ]] && kill -0 "$(cat "$1")" 2>/dev/null; }
port_busy() { ss -ltn 2>/dev/null | awk '{print $4}' | grep -qE "[:.]$1\$"; }
http_ok() { curl -fsS -o /dev/null --max-time 2 "$1" 2>/dev/null; }

free_port() {
  local p="$1" i
  for ((i = 0; i < 20; i++)); do
    port_busy "$p" || { echo "$p"; return 0; }
    p=$((p + 1))
  done
  return 1
}

wait_http() {
  local url="$1" tries="${2:-40}" i
  for ((i = 0; i < tries; i++)); do
    http_ok "$url" && return 0
    sleep 0.25
  done
  return 1
}

needs_build() {
  [[ -f "$OUT/index.html" ]] || return 0
  [[ -n "$(find "$WEB/app" "$WEB/components" "$WEB/lib" "$WEB/data" \
             "$WEB/next.config.mjs" -newer "$OUT/index.html" -print -quit 2>/dev/null)" ]]
}

ensure_deps() {
  command -v npm >/dev/null 2>&1 || die "找不到 npm：先装 Node 18+"
  [[ -x "$WEB/node_modules/.bin/next" ]] && return 0

  say "依赖未安装，正在安装（npm ci）…"
  if [[ -f "$WEB/package-lock.json" ]]; then
    ( cd "$WEB" && npm ci ) || {
      warn "npm ci 失败，改用 npm install 重试"
      ( cd "$WEB" && npm install ) || die "依赖安装失败，看上面的 npm 报错"
    }
  else
    ( cd "$WEB" && npm install ) || die "依赖安装失败，看上面的 npm 报错"
  fi
  [[ -x "$WEB/node_modules/.bin/next" ]] || die "依赖装完仍找不到 next，检查 Node 版本是否 18+"
}

build() {
  ensure_deps
  say "构建 apps/web${BASE_PATH:+（basePath=${BASE_PATH}）}"
  ( cd "$WEB" && NEXT_PUBLIC_BASE_PATH="$BASE_PATH" npm run build ) || die "构建失败"
  touch "$OUT/.nojekyll"   # GitHub Pages 需要，否则 _next/ 会被 Jekyll 忽略
}

start_tunnel() {
  local port="$1" url="" i
  : > "$TUN_LOG"
  say "建立 serveo 隧道…"
  nohup ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        -o ServerAliveInterval=20 -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes \
        -R "80:localhost:$port" serveo.net >"$TUN_LOG" 2>&1 &
  echo $! > "$TUN_PID"

  for ((i = 0; i < 40; i++)); do
    url="$(grep -oE 'https://[a-z0-9-]+\.serveousercontent\.com' "$TUN_LOG" 2>/dev/null | head -1 || true)"
    [[ -n "$url" ]] && break
    sleep 0.5
  done
  [[ -n "$url" ]] || { warn "没拿到隧道地址，日志：$TUN_LOG"; return 1; }
  echo "$url" > "$TUN_URL"

  # serveo 分配后常有十几秒延迟；国内还可能被拦，所以先验一次再报
  if wait_http "$url/" 80; then
    say "公网（临时）：$url"
  else
    warn "隧道地址已生成但暂时不通：${url}（serveo 偶尔要一两分钟生效，用 status 复查）"
  fi
  say "临时地址会断会变；要固定地址请走 GitHub Pages（见 README）"
}

start() {
  local force=0 tunnel=0
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --build)  force=1; shift ;;
      --tunnel) tunnel=1; shift ;;
      --port)   PORT="$2"; shift 2 ;;
      --port=*) PORT="${1#*=}"; shift ;;
      -h|--help) sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
      *) die "未知参数：$1" ;;
    esac
  done

  mkdir -p "$RUN"
  alive "$PID_FILE" && die "已在运行（pid $(cat "$PID_FILE")，端口 $(cat "$PORT_FILE" 2>/dev/null)）；先 stop 或 restart"

  if [[ $force -eq 1 ]] || needs_build; then build; else say "复用已有产物：$OUT"; fi
  [[ -f "$OUT/index.html" ]] || die "没有构建产物：$OUT"

  # 子路径部署要服务父目录，/<repo>/ 才解析得到
  local serve_dir="$OUT"
  if [[ -n "$BASE_PATH" ]]; then
    serve_dir="$RUN/serve-root"
    rm -rf "$serve_dir"; mkdir -p "$serve_dir"
    ln -s "$OUT" "$serve_dir${BASE_PATH%/}"
  fi

  local port; port="$(free_port "$PORT")" || die "端口 $PORT 起连续 20 个都被占用"
  say "启动静态服务 127.0.0.1:${port}（目录 ${serve_dir}）"
  nohup python3 -m http.server "$port" --bind 127.0.0.1 --directory "$serve_dir" >"$LOG_FILE" 2>&1 &
  echo $! > "$PID_FILE"
  echo "$port" > "$PORT_FILE"

  local url="http://127.0.0.1:$port${BASE_PATH%/}/"
  if ! wait_http "$url"; then
    warn "服务没起来，日志：$LOG_FILE"; tail -n 15 "$LOG_FILE" >&2 || true
    stop; exit 1
  fi
  say "本机： $url"

  if [[ $tunnel -eq 1 ]]; then start_tunnel "$port"; else
    say "要公网临时地址：restart --tunnel"
  fi
}

stop() {
  local stopped=0 f pid
  for f in "$TUN_PID" "$PID_FILE"; do
    if alive "$f"; then
      pid="$(cat "$f")"
      kill "$pid" 2>/dev/null || true
      sleep 0.3
      kill -9 "$pid" 2>/dev/null || true
      stopped=1
    fi
    rm -f "$f"
  done
  rm -f "$PORT_FILE" "$TUN_URL"
  [[ $stopped -eq 1 ]] && say "已停止" || say "没有在运行的服务"
}

status() {
  if alive "$PID_FILE"; then
    local port; port="$(cat "$PORT_FILE" 2>/dev/null || echo "")"
    say "服务：运行中（pid $(cat "$PID_FILE")，端口 ${port:-?}）"
    if [[ -n "$port" ]] && http_ok "http://127.0.0.1:$port/"; then
      echo "自检：http://127.0.0.1:$port/ → 200"
    fi
  else
    say "服务：未运行"
  fi
  if alive "$TUN_PID"; then say "隧道：运行中 ${TUN_URL:+$(cat "$TUN_URL" 2>/dev/null)}"
  else say "隧道：未运行"; fi
}

cmd="${1:-start}"
shift || true
case "$cmd" in
  start)   start "$@" ;;
  restart) stop; start "$@" ;;
  stop)    stop ;;
  status)  status ;;
  logs)    tail -n 40 "$LOG_FILE" 2>/dev/null || true; tail -n 20 "$TUN_LOG" 2>/dev/null || true ;;
  *)       die "用法：$0 {start|stop|restart|status|logs} [--build] [--tunnel] [--port N]" ;;
esac
