#!/usr/bin/env python3
"""
Custom GitHub Activity Graph Generator
Renders a sharp, clean, developer-first activity chart (inspired by Grafana & GitHub Insights).
Zero AI fluff: clean axes, sharp grid, precise line geometry, and crisp typography.
"""

import os
import sys
import json
import urllib.request
import subprocess
from datetime import datetime

def get_github_token():
    """Retrieve GitHub token from env or gh CLI."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token
    try:
        token = subprocess.check_output(["gh", "auth", "token"], text=True, stderr=subprocess.DEVNULL).strip()
        if token:
            return token
    except Exception:
        pass
    return None

def fetch_contributions(username, token):
    """Fetch user contribution calendar from GitHub GraphQL API."""
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
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
        "User-Agent": "Antigravity-Activity-Graph/1.0",
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
        return result["data"]["user"]["contributionsCollection"]["contributionCalendar"]

def generate_svg(days_data, total_30d, peak_val, avg_val, username):
    """Render a crisp, human-crafted developer line chart."""
    width = 1100
    height = 320
    
    # Precise margins
    margin_left = 55
    margin_right = 35
    margin_top = 70
    margin_bottom = 50
    
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom
    
    n_days = len(days_data)
    if n_days < 2:
        return ""
    
    step_x = plot_width / (n_days - 1)
    
    # Y-axis calculation: clean step of 2 or 5
    max_count = max(peak_val, 4)
    if max_count <= 6:
        y_max = 6
        y_step = 2
    elif max_count <= 12:
        y_max = 12
        y_step = 3
    elif max_count <= 20:
        y_max = 20
        y_step = 5
    else:
        y_step = 5
        y_max = ((max_count + 4) // 5) * 5
        
    def to_coords(idx, count):
        x = margin_left + idx * step_x
        y = margin_top + plot_height - (count / y_max) * plot_height
        return x, y

    points = [to_coords(i, d["count"]) for i, d in enumerate(days_data)]
    
    # Sharp, precise polyline path (clean engineering look)
    line_path = " ".join([f"{'M' if i == 0 else 'L'} {pt[0]:.2f},{pt[1]:.2f}" for i, pt in enumerate(points)])
    
    # Translucent area fill
    bottom_y = margin_top + plot_height
    area_path = f"{line_path} L {points[-1][0]:.2f},{bottom_y:.2f} L {points[0][0]:.2f},{bottom_y:.2f} Z"
    
    # Clean horizontal gridlines
    grid_lines = []
    num_grid_steps = y_max // y_step
    for i in range(num_grid_steps + 1):
        val = i * y_step
        y_pos = margin_top + plot_height - (val / y_max) * plot_height
        grid_lines.append(f"""
    <line x1="{margin_left}" y1="{y_pos:.1f}" x2="{width - margin_right}" y2="{y_pos:.1f}" stroke="#1e2029" stroke-width="1" />
    <text x="{margin_left - 12}" y="{y_pos + 4:.1f}" text-anchor="end" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Fira Code', monospace" font-size="11" fill="#64748b">{val}</text>""")
        
    # Clean X-axis day labels
    x_labels = []
    for i, d in enumerate(days_data):
        x, y = points[i]
        dt = datetime.strptime(d["date"], "%Y-%m-%d")
        # Label every 2nd day or first/last
        if i % 2 == 0 or i == n_days - 1:
            day_str = dt.strftime("%b %d") if (i == 0 or dt.day == 1) else str(dt.day)
            x_labels.append(f"""
    <line x1="{x:.1f}" y1="{bottom_y}" x2="{x:.1f}" y2="{bottom_y + 5}" stroke="#282a36" stroke-width="1" />
    <text x="{x:.1f}" y="{bottom_y + 20}" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Fira Code', monospace" font-size="11" fill="#64748b">{day_str}</text>""")

    # Sharp data points
    point_elements = []
    for i, d in enumerate(days_data):
        x, y = points[i]
        count = d["count"]
        if count > 0:
            point_elements.append(f"""
    <circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="#08080a" stroke="#ff6b4a" stroke-width="2" />""")

    start_date = datetime.strptime(days_data[0]["date"], "%Y-%m-%d").strftime("%b %d")
    end_date = datetime.strptime(days_data[-1]["date"], "%Y-%m-%d").strftime("%b %d")

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="100%">
  <defs>
    <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#ff6b4a" stop-opacity="0.22" />
      <stop offset="100%" stop-color="#ff6b4a" stop-opacity="0.01" />
    </linearGradient>
  </defs>

  <!-- Frame Background -->
  <rect width="{width}" height="{height}" rx="8" fill="#08080a" stroke="#1f222e" stroke-width="1" />

  <!-- Clean Minimalist Header -->
  <text x="{margin_left}" y="38" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="14" font-weight="600" fill="#f1f5f9" letter-spacing="0.2">Activity · Last 30 Days</text>
  <text x="{margin_left}" y="54" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="12" fill="#64748b">{start_date} – {end_date} · commits, pull requests, reviews, and issues</text>

  <!-- Simple summary stats on right -->
  <text x="{width - margin_right}" y="40" text-anchor="end" font-family="'Fira Code', monospace" font-size="13" font-weight="600" fill="#ff6b4a">
    {total_30d} <tspan fill="#64748b" font-weight="400" font-family="sans-serif" font-size="12">contributions</tspan> &#160;·&#160; <tspan fill="#38bdf8">{peak_val}</tspan> <tspan fill="#64748b" font-weight="400" font-family="sans-serif" font-size="12">peak</tspan> &#160;·&#160; <tspan fill="#94a3b8">{avg_val:.1f}</tspan> <tspan fill="#64748b" font-weight="400" font-family="sans-serif" font-size="12">avg/day</tspan>
  </text>

  <!-- Gridlines -->
  <g id="grid">
    {''.join(grid_lines)}
  </g>

  <!-- Base Baseline -->
  <line x1="{margin_left}" y1="{bottom_y}" x2="{width - margin_right}" y2="{bottom_y}" stroke="#282a36" stroke-width="1" />

  <!-- Shaded Area -->
  <path d="{area_path}" fill="url(#areaGrad)" />

  <!-- Sharp Chart Line -->
  <path d="{line_path}" fill="none" stroke="#ff6b4a" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />

  <!-- Vertices -->
  <g id="points">
    {''.join(point_elements)}
  </g>

  <!-- Day Ticks -->
  <g id="labels">
    {''.join(x_labels)}
  </g>
</svg>
"""
    return svg

def main():
    username = "vanshshah37"
    output_path = os.path.join("assets", "activity-graph.svg")
    os.makedirs("assets", exist_ok=True)
    
    token = get_github_token()
    calendar = fetch_contributions(username, token)
    
    all_days = []
    for week in calendar["weeks"]:
        for day in week["contributionDays"]:
            all_days.append({
                "date": day["date"],
                "count": day["contributionCount"]
            })
            
    recent_days = all_days[-30:]
    counts = [d["count"] for d in recent_days]
    total_30d = sum(counts)
    peak_val = max(counts) if counts else 0
    avg_val = total_30d / len(counts) if counts else 0.0
    
    svg_code = generate_svg(recent_days, total_30d, peak_val, avg_val, username)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_code.strip() + "\n")
        
    print(f"Refined sharp activity graph saved to {output_path}.")

if __name__ == "__main__":
    main()
