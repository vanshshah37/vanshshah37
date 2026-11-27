#!/usr/bin/env python3
"""
Custom GitHub Contributions Over Time Dashboard & Full-Year Frequency Graph
Renders a complete, professional developer dashboard matching the exact layout of
GitHub-Stat-Checker with large, sharp, bold, easily readable typography.
"""

import os
import sys
import json
import urllib.request
import subprocess
from datetime import datetime, timezone

def get_github_token():
    """Retrieve GitHub token from env or gh CLI."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or os.environ.get("PAT_TOKEN")
    if token:
        return token
    try:
        token = subprocess.check_output(["gh", "auth", "token"], text=True, stderr=subprocess.DEVNULL).strip()
        if token:
            return token
    except Exception:
        pass
    return None

def fetch_full_data(username, token):
    """Fetch complete profile stats and 1-year contribution calendar."""
    query = """
    query($login: String!) {
      user(login: $login) {
        createdAt
        contributionsCollection {
          totalCommitContributions
          totalPullRequestContributions
          totalPullRequestReviewContributions
          totalIssueContributions
          restrictedContributionsCount
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                date
                contributionCount
              }
            }
          }
        }
      }
    }
    """
    headers = {
        "User-Agent": "Antigravity-Dashboard/2.0",
        "Content-Type": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    data = json.dumps({"query": query, "variables": {"login": username}}).encode("utf-8")
    req = urllib.request.Request("https://api.github.com/graphql", data=data, headers=headers)
    
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        if "errors" in result:
            raise RuntimeError(f"GraphQL errors: {result['errors']}")
        return result["data"]["user"]

def format_ordinal(n):
    if 11 <= (n % 100) <= 13:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"

def generate_svg(user_data, username):
    created_at_dt = datetime.fromisoformat(user_data["createdAt"].replace("Z", "+00:00"))
    now_dt = datetime.now(timezone.utc)
    
    calendar = user_data["contributionsCollection"]["contributionCalendar"]
    restricted_count = user_data["contributionsCollection"].get("restrictedContributionsCount", 0)
    total_contribs = calendar["totalContributions"]
    public_count = max(0, total_contribs - restricted_count)
    
    # Flatten all contribution days (typically ~370 days / 52 weeks)
    all_days = []
    for week in calendar["weeks"]:
        for day in week["contributionDays"]:
            all_days.append({
                "date": day["date"],
                "count": day["contributionCount"]
            })
            
    # Filter to last 6 months (~182 days / 26 weeks)
    graph_days = all_days[-182:] if len(all_days) >= 182 else all_days
    
    total_days_since_joined = max(1, (now_dt - created_at_dt).days)
    active_days_count = sum(1 for d in all_days if d["count"] > 0)
    
    # Calculate Streaks
    longest_streak = 0
    cur_streak = 0
    for d in all_days:
        if d["count"] > 0:
            cur_streak += 1
            if cur_streak > longest_streak:
                longest_streak = cur_streak
        else:
            cur_streak = 0
            
    # Current streak (reverse traversal)
    current_streak = 0
    rev_days = list(reversed(all_days))
    idx = 0
    if rev_days and rev_days[0]["count"] == 0:
        idx = 1
    while idx < len(rev_days) and rev_days[idx]["count"] > 0:
        current_streak += 1
        idx += 1
        
    # Most productive day (within the 6-month timeframe)
    peak_day_obj = max(graph_days, key=lambda d: d["count"]) if graph_days else {"date": "2026-01-01", "count": 0}
    peak_count = peak_day_obj["count"]
    peak_dt = datetime.strptime(peak_day_obj["date"], "%Y-%m-%d")
    peak_day_str = f"{format_ordinal(peak_dt.day)} {peak_dt.strftime('%b, %Y')}"
    
    # Formatted joined date
    joined_date_str = f"{format_ordinal(created_at_dt.day)} {created_at_dt.strftime('%b, %Y')}"
    years_diff = (now_dt.year - created_at_dt.year)
    months_diff = (now_dt.month - created_at_dt.month)
    if months_diff < 0:
        years_diff -= 1
        months_diff += 12
    joined_subtext = f"{years_diff} year{'s' if years_diff != 1 else ''} {months_diff} month{'s' if months_diff != 1 else ''}"
    
    # SVG Dimensions
    width = 1200
    height = 560
    
    # Layout Coordinates
    # Top Stat Cards (Row of 5 cards with large bold text)
    cards_y = 20
    card_h = 108
    card_gap = 14
    total_cards = 5
    card_w = (width - 40 - (total_cards - 1) * card_gap) / total_cards
    
    cards_data = [
        {
            "label": "Joined GitHub since",
            "val": joined_date_str,
            "sub": f"↑ {joined_subtext}",
            "sub_color": "#22c55e"
        },
        {
            "label": "Total days on GitHub",
            "val": f"{total_days_since_joined} days",
            "sub": f"↑ Active for: {active_days_count} days",
            "sub_color": "#22c55e"
        },
        {
            "label": "Total Contributions",
            "val": f"{total_contribs} commits",
            "sub": f"↑ Public: {public_count} | Private: {restricted_count}",
            "sub_color": "#22c55e"
        },
        {
            "label": "Longest Streak",
            "val": f"{longest_streak} days",
            "sub": f"↑ Current Streak: {current_streak} days",
            "sub_color": "#22c55e" if current_streak > 0 else "#94a3b8"
        },
        {
            "label": "Most Productive Day",
            "val": peak_day_str,
            "sub": f"↑ {peak_count} commits",
            "sub_color": "#22c55e"
        }
    ]
    
    card_svgs = []
    for i, c in enumerate(cards_data):
        cx = 20 + i * (card_w + card_gap)
        card_svgs.append(f"""
    <g transform="translate({cx:.1f}, {cards_y})">
      <rect width="{card_w:.1f}" height="{card_h}" rx="8" fill="#0d1117" stroke="#21262d" stroke-width="1" />
      <text x="18" y="28" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" font-size="13" font-weight="500" fill="#8b949e">{c['label']}</text>
      <text x="18" y="60" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" font-size="22" font-weight="700" fill="#f0f6fc">{c['val']}</text>
      <text x="18" y="90" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" font-size="13" font-weight="600" fill="{c['sub_color']}">{c['sub']}</text>
    </g>""")

    # Chart Section
    chart_title_y = 162
    chart_frame_x = 20
    chart_frame_y = 182
    chart_frame_w = width - 40
    chart_frame_h = 355
    
    margin_left = 75
    margin_right = 35
    margin_top = 40
    margin_bottom = 60
    
    plot_w = chart_frame_w - margin_left - margin_right
    plot_h = chart_frame_h - margin_top - margin_bottom
    
    n_pts = len(graph_days)
    step_x = plot_w / (n_pts - 1) if n_pts > 1 else plot_w
    
    # Y-axis Scale
    y_max_raw = max(peak_count, 10)
    if y_max_raw <= 10:
        y_max = 10
        y_step = 2
    elif y_max_raw <= 20:
        y_max = 20
        y_step = 4
    elif y_max_raw <= 30:
        y_max = 30
        y_step = 5
    else:
        y_step = 10
        y_max = ((y_max_raw + 9) // 10) * 10
        
    def to_coords(idx, count):
        x = chart_frame_x + margin_left + idx * step_x
        y = chart_frame_y + margin_top + plot_h - (count / y_max) * plot_h
        return x, y

    points = [to_coords(i, d["count"]) for i, d in enumerate(graph_days)]
    
    # Sharp polyline path
    line_path = " ".join([f"{'M' if i == 0 else 'L'} {pt[0]:.2f},{pt[1]:.2f}" for i, pt in enumerate(points)])
    
    # Translucent area fill
    bottom_y = chart_frame_y + margin_top + plot_h
    area_path = f"{line_path} L {points[-1][0]:.2f},{bottom_y:.2f} L {points[0][0]:.2f},{bottom_y:.2f} Z"
    
    # Grid lines & Y labels (Clear, larger font)
    grid_svgs = []
    num_grid_steps = y_max // y_step
    for i in range(num_grid_steps + 1):
        val = i * y_step
        y_pos = chart_frame_y + margin_top + plot_h - (val / y_max) * plot_h
        grid_svgs.append(f"""
    <line x1="{chart_frame_x + margin_left}" y1="{y_pos:.1f}" x2="{chart_frame_x + chart_frame_w - margin_right}" y2="{y_pos:.1f}" stroke="#1f242c" stroke-width="1" />
    <text x="{chart_frame_x + margin_left - 12}" y="{y_pos + 4.5:.1f}" text-anchor="end" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', monospace" font-size="13" font-weight="600" fill="#8b949e">{val}</text>""")
        
    # X labels: every ~2-3 weeks (spaced cleanly across 6 months)
    x_label_svgs = []
    label_step = max(1, n_pts // 12)
    labeled_indices = sorted(set(list(range(0, n_pts, label_step)) + [n_pts - 1]))
    for i in labeled_indices:
        x, y = points[i]
        dt = datetime.strptime(graph_days[i]["date"], "%Y-%m-%d")
        date_str = dt.strftime("%b %d")
        x_label_svgs.append(f"""
    <line x1="{x:.1f}" y1="{bottom_y}" x2="{x:.1f}" y2="{bottom_y + 6}" stroke="#282e38" stroke-width="1" />
    <text x="{x:.1f}" y="{bottom_y + 24}" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" font-size="12.5" font-weight="500" fill="#8b949e">{date_str}</text>""")

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="100%">
  <defs>
    <linearGradient id="emeraldArea" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#22c55e" stop-opacity="0.25" />
      <stop offset="100%" stop-color="#22c55e" stop-opacity="0.0" />
    </linearGradient>
  </defs>

  <!-- Canvas Background -->
  <rect width="{width}" height="{height}" fill="#08080a" />

  <!-- Top Metric Cards -->
  <g id="top-cards">
    {''.join(card_svgs)}
  </g>

  <!-- Section Title -->
  <text x="20" y="{chart_title_y}" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="22" font-weight="700" fill="#f0f6fc" letter-spacing="0.2">Contributions Over Time <tspan font-size="14" font-weight="500" fill="#8b949e">&#183; Last 6 Months</tspan></text>

  <!-- Main Chart Frame -->
  <rect x="{chart_frame_x}" y="{chart_frame_y}" width="{chart_frame_w}" height="{chart_frame_h}" rx="8" fill="#0d1117" stroke="#21262d" stroke-width="1" />

  <!-- Y Axis Title (Rotated) -->
  <text transform="rotate(-90)" x="-{chart_frame_y + (chart_frame_h / 2):.1f}" y="{chart_frame_x + 28}" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" font-size="14" font-weight="600" fill="#8b949e" letter-spacing="0.5">Contributions</text>

  <!-- X Axis Title (Bottom Centered) -->
  <text x="{chart_frame_x + (chart_frame_w / 2):.1f}" y="{chart_frame_y + chart_frame_h - 12}" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" font-size="14" font-weight="600" fill="#8b949e" letter-spacing="0.5">Date</text>

  <!-- Horizontal Grid Lines -->
  <g id="grid-lines">
    {''.join(grid_svgs)}
  </g>

  <!-- Baseline -->
  <line x1="{chart_frame_x + margin_left}" y1="{bottom_y}" x2="{chart_frame_x + chart_frame_w - margin_right}" y2="{bottom_y}" stroke="#21262d" stroke-width="1" />

  <!-- Area Fill -->
  <path d="{area_path}" fill="url(#emeraldArea)" />

  <!-- High-Frequency Activity Line (Emerald Neon) -->
  <path d="{line_path}" fill="none" stroke="#22c55e" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round" />

  <!-- X Axis Date Labels -->
  <g id="x-axis-labels">
    {''.join(x_label_svgs)}
  </g>
</svg>
"""
    return svg

def main():
    username = "vanshshah37"
    output_path = os.path.join("assets", "activity-graph.svg")
    os.makedirs("assets", exist_ok=True)
    
    token = get_github_token()
    print(f"Fetching full 365-day dataset for @{username}...")
    user_data = fetch_full_data(username, token)
    
    svg_code = generate_svg(user_data, username)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_code.strip() + "\n")
        
    print(f"Successfully generated full-year dashboard at {output_path} ({len(svg_code)} bytes).")

if __name__ == "__main__":
    main()
