# NBA Statistics MCP Server

A Model Context Protocol (MCP) server that exposes NBA player statistics through tools that can be used by Claude or other MCP clients.

## Features

- **get_player_points_history**: Get detailed game-by-game scoring history for any player
- **get_player_split_stats**: Analyze player performance splits (home/away or by rest days)

## Installation

1. Install dependencies:
```bash
pip install -r requirements-mcp.txt
```

## Usage

### Running the Server

Start the MCP server:

```bash
python nba_local_server.py
```

The server will load the NBA data from `nba-stats/` directory at startup.

### Configuring Claude Desktop

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "nba-local": {
      "command": "/Users/adriangri/.pyenv/versions/3.11.14/bin/python",
      "args": ["/Users/adriangri/programming/nba-mcp/nba_local_server.py"]
    }
  }
}
```

**Important:** Use the full path to the pyenv Python executable. This ensures Claude Desktop can find the correct Python with all dependencies installed.

### Available Tools

#### 1. get_player_points_history

Get a player's scoring history across seasons.

**Parameters:**
- `player_name` (str): Player's name (supports partial matches)
- `season_start` (int): Starting season year (e.g., 2023 for 2023-24)
- `season_end` (int): Ending season year
- `max_games` (int, optional): Max recent games to return (default: 82)

**Example:**
```python
get_player_points_history(
    player_name="LeBron James",
    season_start=2022,
    season_end=2024,
    max_games=50
)
```

**Returns:**
- Player info and identification
- Game-by-game scoring data with shooting stats
- Summary statistics (home vs away averages)

#### 2. get_player_split_stats

Analyze player performance by splits.

**Parameters:**
- `player_name` (str): Player's name
- `split` (str): "home_away" or "rest_days"
- `season_start` (int, optional): Starting season (default: 2020)
- `season_end` (int, optional): Ending season (default: 2024)

**Example:**
```python
get_player_split_stats(
    player_name="Stephen Curry",
    split="home_away",
    season_start=2022,
    season_end=2024
)
```

**Returns:**
For home_away:
- Performance stats for home games
- Performance stats for away games
- Shooting percentages for each

For rest_days:
- Performance on back-to-backs
- Performance with 1, 2, or 3+ days rest
- Shows impact of rest on player performance

## Data Structure

The server loads three CSV files at startup:
- `Players.csv`: Player information and IDs
- `PlayerStatistics.csv`: Game-by-game player stats
- `Games.csv`: Game metadata

## Design Decisions

- **Small Responses**: Tools limit data returned (max 82 games by default) to avoid overwhelming clients
- **Pandas over Spark**: Uses pandas for lightweight local server operation
- **Normalized Names**: Supports flexible player name searching (partial matches)
- **Pre-computed Seasons**: Calculates NBA seasons at load time for faster queries
- **Minutes Filtering**: Excludes games where player didn't actually play (0 minutes)

## Example Queries for Claude

Once configured, you can ask Claude:

- "Show me LeBron James' scoring over the last 3 seasons"
- "How does Stephen Curry perform at home vs away?"
- "Does Giannis score differently on back-to-back games?"
- "Get Luka Doncic's last 40 games"
