"""
Script to render a static HTML leaderboard from the JSON results.
Usage: python scripts/render_leaderboard.py [results_file.json]
"""
import json
import sys
from datetime import datetime
from pathlib import Path

TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AlphaEvolve AgentX Leaderboard</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px; background: #f5f7fa; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .card { background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); padding: 20px; margin-bottom: 20px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { text-align: left; padding: 12px; border-bottom: 1px solid #eee; }
        th { color: #666; font-size: 0.9em; text-transform: uppercase; letter-spacing: 0.5px; }
        .rank { font-weight: bold; color: #764ba2; font-size: 1.2em; }
        .score { font-family: 'Courier New', monospace; font-weight: bold; }
        .badge { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 0.8em; margin-right: 5px; }
        .badge-green { background: #e6fffa; color: #2c7a7b; }
        .badge-purple { background: #faf5ff; color: #553c9a; }
    </style>
</head>
<body>
    <div class="header">
        <h1>AlphaEvolve AgentX Leaderboard</h1>
        <p>Phase 1: Green Agent Evaluation</p>
    </div>

    <div class="card">
        <h2>🏆 Agent Rankings</h2>
        <table>
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Agent</th>
                    <th>Average Score</th>
                    <th>Consistency</th>
                    <th>Runs</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
    </div>

    <div class="card">
        <h2>📊 Statistics</h2>
        <p><strong>Total Runs:</strong> {total_runs}</p>
        <p><strong>Last Updated:</strong> {generated_at}</p>
        <p><strong>Reproducibility:</strong> <span class="badge badge-green">{reproducibility_status}</span></p>
    </div>
</body>
</html>
"""

def render_leaderboard(results_path: str = "results/evaluation_results.json"):
    path = Path(results_path)
    if not path.exists():
        print(f"Error: Results file not found at {path}")
        return

    with open(path) as f:
        data = json.load(f)

    leaderboard = data.get("leaderboard", {})
    entries = leaderboard.get("entries", [])
    
    rows = []
    for entry in entries:
        std_dev = entry.get("std_dev", 0.0)
        consistency = f"±{std_dev:.2f}" if std_dev > 0 else "Perfect"
        
        row = f"""
        <tr>
            <td class="rank">#{entry.get('rank', '-')}</td>
            <td><span class="badge badge-purple">{entry.get('agent', 'Unknown')}</span></td>
            <td class="score">{entry.get('average_score', 0.0):.1f}%</td>
            <td>{consistency}</td>
            <td>{entry.get('run_count', 0)}</td>
        </tr>
        """
        rows.append(row)

    html = TEMPLATE.format(
        rows="\n".join(rows) if rows else "<tr><td colspan='5'>No results yet</td></tr>",
        total_runs=leaderboard.get("metadata", {}).get("total_runs", 0),
        generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        reproducibility_status="Verified" if std_dev < 1.0 else "Pending"
    )

    out_path = path.parent / "leaderboard.html"
    with open(out_path, "w") as f:
        f.write(html)
    
    print(f"Leaderboard generated at: {out_path}")

if __name__ == "__main__":
    file_path = sys.argv[1] if len(sys.argv) > 1 else "results/evaluation_results.json"
    render_leaderboard(file_path)
