#!/usr/bin/env python3
"""
Custom GitHub Activity & Contribution Flow Graph Generator
Fetches accurate contribution calendar data (Commits, PRs, Code Reviews, Issues)
from GitHub's official GraphQL API and renders a high-precision, dark-mode SVG.
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
    else:
        print("Warning: No GITHUB_TOKEN found. GraphQL query may fail for private or rate-limited requests.")

    data = json.dumps({"query": query, "variables": {"login": username}}).encode("utf-8")
    req = urllib.request.Request("https://api.github.com/graphql", data=data, headers=headers)
    
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        if "errors" in result:
            raise RuntimeError(f"GraphQL errors: {result['errors']}")
        return result["data"]["user"]["contributionsCollection"]["contributionCalendar"]

def generate_svg(days_data, total_30d, peak_val, avg_val, username):
    """Render dark-mode responsive SVG line graph matching Vanshs theme."""
    width = 1200
    height = 370
    
    # Chart margins
    margin_left = 65
    margin_right = 45
    margin_top = 100
    margin_bottom = 60
    
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom
    
    n_days = len(days_data)
    if n_days < 2:
        return ""
    
    step_x = plot_width / (n_days - 1)
    
    # Calculate Y scale (max at least 5 for aesthetics)
    max_count = max(peak_val, 5)
    # Round up max_count to next nice multiple
    if max_count <= 5:
        y_max = 5
    elif max_count <= 10:
        y_max = 10
    elif max_count <= 20:
        y_max = 20
    else:
        y_max = ((max_count + 4) // 5) * 5
        
    def to_coords(idx, count):
        x = margin_left + idx * step_x
        y = margin_top + plot_height - (count / y_max) * plot_height
        return x, y

    points = [to_coords(i, d["count"]) for i, d in enumerate(days_data)]
    
    # Build smooth cubic bezier path
    # Control points using smooth tension
    path_d = [f"M {points[0][0]:.2f} {points[0][1]:.2f}"]
    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        
        # Smooth horizontal tangency
        cx0 = x0 + (x1 - x0) * 0.45
        cy0 = y0
        cx1 = x1 - (x1 - x0) * 0.45
        cy1 = y1
        path_d.append(f"C {cx0:.2f} {cy0:.2f}, {cx1:.2f} {cy1:.2f}, {x1:.2f} {y1:.2f}")
        
    line_path = " ".join(path_d)
    
    # Area path closed to bottom
    bottom_y = margin_top + plot_height
    area_path = f"{line_path} L {points[-1][0]:.2f} {bottom_y:.2f} L {points[0][0]:.2f} {bottom_y:.2f} Z"
    
    # Horizontal grid lines (4 intervals)
    grid_lines = []
    y_steps = 4
    for i in range(y_steps + 1):
        val = int(round((y_max / y_steps) * i))
        y_pos = margin_top + plot_height - (val / y_max) * plot_height
        grid_lines.append(f"""
        <line x1="{margin_left}" y1="{y_pos:.1f}" x2="{width - margin_right}" y2="{y_pos:.1f}" stroke="#1e1e26" stroke-width="1" stroke-dasharray="3,3" />
        <text x="{margin_left - 15}" y="{y_pos + 4:.1f}" text-anchor="end" font-family="'Fira Code', monospace, sans-serif" font-size="11" fill="#64748b">{val}</text>
        """)
        
    # Vertical day labels (every 2-3 days or day of month)
    x_labels = []
    for i, d in enumerate(days_data):
        x, y = points[i]
        # Show day every 2 or 3 days or first/last
        if i % 2 == 0 or i == n_days - 1:
            dt = datetime.strptime(d["date"], "%Y-%m-%d")
            day_str = dt.strftime("%d %b") if (i == 0 or dt.day == 1 or i == n_days - 1) else str(dt.day)
            x_labels.append(f"""
            <line x1="{x:.1f}" y1="{bottom_y}" x2="{x:.1f}" y2="{bottom_y + 6}" stroke="#2d2d38" stroke-width="1" />
            <text x="{x:.1f}" y="{bottom_y + 22}" text-anchor="middle" font-family="'Fira Code', monospace, sans-serif" font-size="11" fill="#64748b">{day_str}</text>
            """)

    # Interactive/aesthetic data dots
    point_elements = []
    for i, d in enumerate(days_data):
        x, y = points[i]
        count = d["count"]
        if count > 0:
            point_elements.append(f"""
            <circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="#08080a" stroke="#ff6b4a" stroke-width="2.5" />
            <circle cx="{x:.1f}" cy="{y:.1f}" r="1.5" fill="#38bdf8" />
            """)
        else:
            point_elements.append(f"""
            <circle cx="{x:.1f}" cy="{y:.1f}" r="2" fill="#2d2d38" />
            """)

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="100%">
  <defs>
    <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#ff6b4a" stop-opacity="0.32" />
      <stop offset="65%" stop-color="#38bdf8" stop-opacity="0.08" />
      <stop offset="100%" stop-color="#08080a" stop-opacity="0.0" />
    </linearGradient>
    <linearGradient id="lineGradient" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#38bdf8" />
      <stop offset="70%" stop-color="#ff6b4a" />
      <stop offset="100%" stop-color="#ff8e75" />
    </linearGradient>
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="4" result="glow" />
      <feComposite in="SourceGraphic" in2="glow" operator="over" />
    </filter>
  </defs>

  <!-- Card Background -->
  <rect width="{width}" height="{height}" rx="12" fill="#08080a" stroke="#252530" stroke-width="1.2" />

  <!-- Top Header -->
  <g id="header">
    <!-- Pulse Indicator -->
    <circle cx="{margin_left + 4}" cy="42" r="4.5" fill="#22c55e" />
    <circle cx="{margin_left + 4}" cy="42" r="8" fill="none" stroke="#22c55e" stroke-width="1" opacity="0.4" />
    
    <text x="{margin_left + 22}" y="47" font-family="'Fira Code', 'Segoe UI', monospace" font-size="16" font-weight="700" fill="#f8fafc" letter-spacing="0.5">
      CONTRIBUTION &amp; CODE ACTIVITY FLOW
    </text>
    <text x="{margin_left + 22}" y="68" font-family="'Segoe UI', sans-serif" font-size="12" fill="#94a3b8">
      Real-time rolling 30-day velocity · Commits, Pull Requests, Code Reviews &amp; Issues
    </text>

    <!-- Stat Badges (Right aligned) -->
    <g transform="translate({width - margin_right - 350}, 28)">
      <!-- Total 30D -->
      <rect x="0" y="0" width="105" height="46" rx="8" fill="#121217" stroke="#252530" stroke-width="1" />
      <text x="52" y="18" text-anchor="middle" font-family="'Segoe UI', sans-serif" font-size="10" font-weight="600" fill="#94a3b8" letter-spacing="0.5">TOTAL (30D)</text>
      <text x="52" y="38" text-anchor="middle" font-family="'Fira Code', monospace" font-size="16" font-weight="700" fill="#ff6b4a">{total_30d}</text>

      <!-- Peak Day -->
      <rect x="115" y="0" width="105" height="46" rx="8" fill="#121217" stroke="#252530" stroke-width="1" />
      <text x="167" y="18" text-anchor="middle" font-family="'Segoe UI', sans-serif" font-size="10" font-weight="600" fill="#94a3b8" letter-spacing="0.5">PEAK VELOCITY</text>
      <text x="167" y="38" text-anchor="middle" font-family="'Fira Code', monospace" font-size="16" font-weight="700" fill="#38bdf8">{peak_val}/day</text>

      <!-- Avg / Day -->
      <rect x="230" y="0" width="105" height="46" rx="8" fill="#121217" stroke="#252530" stroke-width="1" />
      <text x="282" y="18" text-anchor="middle" font-family="'Segoe UI', sans-serif" font-size="10" font-weight="600" fill="#94a3b8" letter-spacing="0.5">DAILY AVERAGE</text>
      <text x="282" y="38" text-anchor="middle" font-family="'Fira Code', monospace" font-size="16" font-weight="700" fill="#e2e8f0">{avg_val:.1f}</text>
    </g>
  </g>

  <!-- Grid Lines -->
  <g id="grid">
    {''.join(grid_lines)}
  </g>

  <!-- Area Fill -->
  <path d="{area_path}" fill="url(#areaGradient)" />

  <!-- Smooth Flow Line -->
  <path d="{line_path}" fill="none" stroke="url(#lineGradient)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />

  <!-- Data Point Circles -->
  <g id="points">
    {''.join(point_elements)}
  </g>

  <!-- X-Axis Labels -->
  <g id="x-axis">
    {''.join(x_labels)}
  </g>
</svg>
"""
    return svg_content

def main():
    username = "vanshshah37"
    output_path = os.path.join("assets", "activity-graph.svg")
    os.makedirs("assets", exist_ok=True)
    
    token = get_github_token()
    print(f"Fetching contribution data for @{username}...")
    calendar = fetch_contributions(username, token)
    
    # Flatten all contribution days
    all_days = []
    for week in calendar["weeks"]:
        for day in week["contributionDays"]:
            all_days.append({
                "date": day["date"],
                "count": day["contributionCount"]
            })
            
    # Filter to last 31 days
    recent_days = all_days[-31:]
    
    counts = [d["count"] for d in recent_days]
    total_30d = sum(counts)
    peak_val = max(counts) if counts else 0
    avg_val = total_30d / len(counts) if counts else 0.0
    
    print(f"Extracted {len(recent_days)} days:")
    print(f"Total (30D): {total_30d} | Peak: {peak_val} | Avg: {avg_val:.2f}")
    print(f"Latest Day ({recent_days[-1]['date']}): {recent_days[-1]['count']} contributions")
    if len(recent_days) >= 2:
        print(f"Previous Day ({recent_days[-2]['date']}): {recent_days[-2]['count']} contributions")
        
    svg_code = generate_svg(recent_days, total_30d, peak_val, avg_val, username)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_code.strip() + "\n")
        
    print(f"Successfully generated {output_path} ({len(svg_code)} bytes).")

if __name__ == "__main__":
    main()
