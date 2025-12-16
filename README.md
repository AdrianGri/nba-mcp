# NBA Analytics with Model Context Protocol

A comprehensive NBA analytics project that combines historical basketball statistics with AI-powered analysis through the Model Context Protocol (MCP). This project enables intelligent exploration of player performance, contextual trends, and team evolution from 1947 to today.

## Project Overview

This project investigates how NBA player performance depends on context and how both players and teams change over time. It explores questions like:

- When do players tend to exceed or fall short of their recent averages?
- How do rest and schedule density affect different types of players?
- Does opponent quality or home court have noticeable effects on scoring or efficiency?
- How have teams' offensive profiles changed across seasons?

### Core Components

1. **MCP Server** ([nba_local_server.py](nba_local_server.py)) - An intelligent analytics agent that exposes tools for querying NBA statistics via the Model Context Protocol
2. **Data Preview Notebook** ([nba_data_preview.ipynb](nba_data_preview.ipynb)) - Explore dataset structure, schemas, and sample data
3. **Analysis Notebook** ([nba_player_team_analysis.ipynb](nba_player_team_analysis.ipynb)) - Visualization functions for player and team performance trends
4. **Dataset Updater** ([update_nba_dataset.ipynb](update_nba_dataset.ipynb)) - Tools for updating the NBA statistics dataset

## Dataset

**Source**: [NBA Dataset - Box Scores & Stats, 1947 - Today](https://www.kaggle.com/datasets/wyattowalsh/basketball)

The dataset includes comprehensive statistics stored in the `nba-stats/` directory:

- **Games.csv** - Game-level information and results
- **Players.csv** - Player biographical information
- **PlayerStatistics.csv** - Detailed player performance stats for every game
- **TeamHistories.csv** - Team franchise history and relocations
- **TeamStatistics.csv** - Team-level performance data
- **LeagueSchedule24_25.csv** & **LeagueSchedule25_26.csv** - Future game schedules

## Getting Started

### Prerequisites

- Python 3.11+
- pip package manager

### Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd nba-mcp
```

2. Install dependencies:
```bash
pip install -r requirements-mcp.txt
```

For Spark-based analysis notebooks, you'll also need:
```bash
pip install pyspark py4j matplotlib
```

## Usage

### 1. MCP Server - AI-Powered Analytics

The MCP server enables LLMs like Claude to query NBA statistics intelligently. See [README-MCP.md](README-MCP.md) for detailed setup instructions.

**Quick Start:**

```bash
python nba_local_server.py
```

**Available Tools:**

1. **`get_player_boxscore_history`** - Get complete boxscore stats from a player's last game against a specific opponent
   - Full stats: points, rebounds, assists, steals, blocks, shooting percentages
   - Filter by home/away games
   - Includes game context (win/loss, plus/minus)

2. **`get_player_split_stats`** - Analyze player performance splits
   - Home/Away splits with shooting percentages
   - Rest days analysis (back-to-back, 1 day, 2 days, 3+ days rest)
   - Customizable season ranges

3. **`get_team_points_history`** - Track team scoring across seasons
   - Game-by-game scoring with opponent information
   - Home/away performance breakdowns
   - Win/loss records and shooting percentages

4. **`get_stat_history`** - Deep dive into specific player statistics
   - Tracks: points, rebounds, assists, 3-pointers, blocks
   - Last N games with full context
   - Summary statistics (average, max, min)

**Example Queries (via Claude):**
- "What did LeBron James score the last time he played the Warriors?"
- "How does LeBron perform on the second night of a back-to-back?"
- "Show me Stephen Curry's 3-point shooting over his last 15 games"
- "Get the Lakers' scoring trend for the 2023-24 season"
- "Compare Giannis's home vs away performance over the last 3 seasons"

**Integration with Claude Desktop:**

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "nba-local": {
      "command": "/path/to/python",
      "args": ["/path/to/nba_local_server.py"]
    }
  }
}
```

### 2. Data Exploration

Use [nba_data_preview.ipynb](nba_data_preview.ipynb) to:
- Load all NBA datasets into Spark DataFrames
- Examine schemas and data types
- View sample records
- Understand available statistics and relationships

**Example:**
```python
# After running the notebook cells
print(f"Total games: {games_df.count():,}")
print(f"Total players: {players_df.count():,}")
players_df.show(5)
```

### 3. Performance Analysis

Use [nba_player_team_analysis.ipynb](nba_player_team_analysis.ipynb) for visualization and trend analysis:

**Player Point History:**
```python
# Visualize scoring trends over time
get_player_point_history("LeBron James", numPastSeasons=3, 
                         games_per_point=1, show_home=True, show_away=True)
```

**Team Performance:**
```python
# Track team scoring patterns
get_team_point_history("Warriors", numPastSeasons=2, 
                       games_per_point=1, show_home=True, show_away=False)
```

**Stat-Specific Analysis:**
```python
# Deep dive into specific statistics
get_stat_history("Stephen Curry", stat="3_pointers", num_past_games=15)
```

Available stats: `"points"`, `"rebounds"`, `"assists"`, `"3_pointers"`, `"blocks"`

### 4. Dataset Updates

Use [update_nba_dataset.ipynb](update_nba_dataset.ipynb) to refresh the dataset with the latest NBA statistics.

## Project Structure

```
nba-mcp/
├── README.md                      # This file
├── README-MCP.md                  # MCP server documentation
├── requirements-mcp.txt           # Python dependencies
├── nba_local_server.py           # MCP server implementation
├── nba_data_preview.ipynb        # Dataset exploration notebook
├── nba_player_team_analysis.ipynb # Analysis & visualization notebook
├── update_nba_dataset.ipynb      # Dataset update tools
└── nba-stats/                    # CSV data files
    ├── Games.csv
    ├── Players.csv
    ├── PlayerStatistics.csv
    ├── TeamHistories.csv
    ├── TeamStatistics.csv
    ├── LeagueSchedule24_25.csv
    └── LeagueSchedule25_26.csv
```
