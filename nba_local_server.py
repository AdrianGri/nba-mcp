"""
NBA Statistics MCP Server

Exposes NBA player statistics through MCP tools.
"""

import sys
import os
import pandas as pd
from datetime import datetime
from typing import Literal
from mcp.server.fastmcp import FastMCP

# Initialize MCP server
mcp = FastMCP("nba-local")

# Global DataFrames - loaded once at startup
PLAYERS_DF = None
PLAYER_STATS_DF = None
GAMES_DF = None
TEAM_HISTORIES_DF = None
TEAM_STATS_DF = None


def load_data():
    """Load NBA data at startup"""
    global PLAYERS_DF, PLAYER_STATS_DF, GAMES_DF, TEAM_HISTORIES_DF, TEAM_STATS_DF
    
    print("Loading NBA data...", file=sys.stderr)
    
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.join(script_dir, "nba-stats/")
    
    # Load CSVs
    PLAYERS_DF = pd.read_csv(os.path.join(base_path, "Players.csv"))
    PLAYER_STATS_DF = pd.read_csv(os.path.join(base_path, "PlayerStatistics.csv"), low_memory=False)
    GAMES_DF = pd.read_csv(os.path.join(base_path, "Games.csv"), low_memory=False)
    TEAM_HISTORIES_DF = pd.read_csv(os.path.join(base_path, "TeamHistories.csv"))
    TEAM_STATS_DF = pd.read_csv(os.path.join(base_path, "TeamStatistics.csv"), low_memory=False)
    
    # Add normalized player names for easier searching
    PLAYERS_DF["fullName"] = PLAYERS_DF["firstName"] + " " + PLAYERS_DF["lastName"]
    PLAYERS_DF["fullName_norm"] = PLAYERS_DF["fullName"].str.strip().str.lower()
    
    # Convert dates - handle mixed timezone formats efficiently
    # Some dates have 'Z' suffix (UTC), others don't
    print("Parsing dates...", file=sys.stderr)
    
    # First, try to parse everything uniformly
    PLAYER_STATS_DF["gameDate"] = pd.to_datetime(PLAYER_STATS_DF["gameDate"], errors='coerce', format='mixed', utc=True)
    
    # Convert UTC to naive (remove timezone info) 
    PLAYER_STATS_DF["gameDate"] = PLAYER_STATS_DF["gameDate"].dt.tz_convert(None)
    
    # Parse minutes (handle both MM:SS and decimal formats)
    def parse_minutes(mins):
        if pd.isna(mins):
            return 0.0
        mins_str = str(mins)
        if ":" in mins_str:
            try:
                parts = mins_str.split(":")
                return float(parts[0]) + float(parts[1]) / 60
            except:
                return 0.0
        try:
            return float(mins_str)
        except:
            return 0.0
    
    PLAYER_STATS_DF["minutes_decimal"] = PLAYER_STATS_DF["numMinutes"].apply(parse_minutes)
    
    # Filter out rows with invalid dates
    PLAYER_STATS_DF = PLAYER_STATS_DF[PLAYER_STATS_DF["gameDate"].notna()].copy()
    
    # Extract season from date (NBA season spans two years, e.g., 2023-24)
    # A game in Nov 2023 - June 2024 is the 2023-24 season
    PLAYER_STATS_DF["year"] = PLAYER_STATS_DF["gameDate"].dt.year
    PLAYER_STATS_DF["month"] = PLAYER_STATS_DF["gameDate"].dt.month
    PLAYER_STATS_DF["season"] = PLAYER_STATS_DF.apply(
        lambda row: row["year"] - 1 if row["month"] <= 6 else row["year"], axis=1
    )
    
    # Parse team stats dates
    TEAM_STATS_DF["gameDate"] = pd.to_datetime(TEAM_STATS_DF["gameDate"], errors='coerce', format='mixed', utc=True)
    TEAM_STATS_DF["gameDate"] = TEAM_STATS_DF["gameDate"].dt.tz_convert(None)
    TEAM_STATS_DF = TEAM_STATS_DF[TEAM_STATS_DF["gameDate"].notna()].copy()
    
    print(f"Loaded {len(PLAYERS_DF)} players", file=sys.stderr)
    print(f"Loaded {len(PLAYER_STATS_DF)} player statistics records", file=sys.stderr)
    print(f"Loaded {len(GAMES_DF)} games", file=sys.stderr)
    print(f"Loaded {len(TEAM_HISTORIES_DF)} team histories", file=sys.stderr)
    print(f"Loaded {len(TEAM_STATS_DF)} team statistics records", file=sys.stderr)
    
    # Debug: Show season range in data
    if len(PLAYER_STATS_DF) > 0:
        min_season = PLAYER_STATS_DF["season"].min()
        max_season = PLAYER_STATS_DF["season"].max()
        print(f"Season range in data: {min_season} to {max_season}", file=sys.stderr)
    
    print("Data loading complete!", file=sys.stderr)


def normalize_name(name: str) -> str:
    """Normalize player name for searching"""
    return name.strip().lower()


def find_player(player_name: str):
    """Find player by name (supports partial matches)"""
    search_term = normalize_name(player_name)
    
    # Try exact match first
    match = PLAYERS_DF[PLAYERS_DF["fullName_norm"] == search_term]
    if not match.empty:
        return match.iloc[0]
    
    # Try partial match
    match = PLAYERS_DF[
        PLAYERS_DF["fullName_norm"].str.contains(search_term) |
        PLAYERS_DF["firstName"].str.lower().str.contains(search_term) |
        PLAYERS_DF["lastName"].str.lower().str.contains(search_term)
    ]
    
    if match.empty:
        return None
    
    return match.iloc[0]

def find_team(team_name: str):
    """Find team by name, abbreviation, or city (supports partial matches, prioritizes active teams)"""
    search_term = normalize_name(team_name)
    
    # Search in teamName, teamAbbrev, and teamCity
    match = TEAM_HISTORIES_DF[
        TEAM_HISTORIES_DF["teamName"].str.lower().str.contains(search_term) |
        TEAM_HISTORIES_DF["teamAbbrev"].str.lower().str.contains(search_term) |
        TEAM_HISTORIES_DF["teamCity"].str.lower().str.contains(search_term)
    ]
    
    if match.empty:
        return None
    
    # Sort by seasonActiveTill (null means active) to prioritize current teams
    match = match.sort_values("seasonActiveTill", ascending=False, na_position='first')
    
    return match.iloc[0]

@mcp.tool()
def get_player_points_history(
    player_name: str,
    season_start: int,
    season_end: int,
    max_games: int = 82
) -> dict:
    """
    Get a player's scoring history across multiple seasons.
    
    Args:
        player_name: Player's first name, last name, or full name
        season_start: Starting season year (e.g., 2021 for 2021-22 season)
        season_end: Ending season year (e.g., 2024 for 2024-25 season)
        max_games: Maximum number of most recent games to return (default: 82)
    
    Returns:
        Dictionary with player info and game-by-game scoring data
    """
    # Find player
    player = find_player(player_name)
    if player is None:
        return {"error": f"Player '{player_name}' not found"}
    
    player_id = player["personId"]
    full_name = player["fullName"]
    
    # Convert season years to date range (like the notebook does)
    # Season 2021 means 2021-22 season, which starts in Oct 2021
    # So we want games from Oct season_start through June season_end+1
    start_date = pd.Timestamp(f"{season_start}-10-01")
    end_date = pd.Timestamp(f"{season_end + 1}-09-30")
    
    # Filter player stats by player ID and date range (exactly like notebook)
    stats = PLAYER_STATS_DF[
        (PLAYER_STATS_DF["personId"] == player_id) &
        (PLAYER_STATS_DF["gameDate"] >= start_date) &
        (PLAYER_STATS_DF["gameDate"] <= end_date) &
        (PLAYER_STATS_DF["minutes_decimal"] > 0) &
        (PLAYER_STATS_DF["points"].notna())
    ].copy()
    
    if stats.empty:
        return {
            "player": full_name,
            "player_id": int(player_id),
            "season_range": f"{season_start}-{season_end}",
            "games": [],
            "message": "No games found for this player in the specified seasons"
        }
    
    # Sort by date and take most recent games
    stats = stats.sort_values("gameDate", ascending=False).head(max_games)
    stats = stats.sort_values("gameDate")  # Re-sort chronologically
    
    # Prepare output
    games = []
    for _, row in stats.iterrows():
        games.append({
            "date": row["gameDate"].strftime("%Y-%m-%d"),
            "season": int(row["season"]),
            "points": int(row["points"]),
            "minutes": round(row["minutes_decimal"], 1),
            "home": bool(row["home"]),
            "field_goals": f"{int(row['fieldGoalsMade'])}/{int(row['fieldGoalsAttempted'])}",
            "three_pointers": f"{int(row['threePointersMade'])}/{int(row['threePointersAttempted'])}",
            "free_throws": f"{int(row['freeThrowsMade'])}/{int(row['freeThrowsAttempted'])}"
        })
    
    # Calculate summary stats
    total_points = stats["points"].sum()
    avg_points = stats["points"].mean()
    home_games = stats[stats["home"] == 1]
    away_games = stats[stats["home"] == 0]
    
    return {
        "player": full_name,
        "player_id": int(player_id),
        "season_range": f"{season_start}-{season_end}",
        "total_games": len(games),
        "summary": {
            "total_points": int(total_points),
            "avg_points": round(avg_points, 1),
            "home_games": len(home_games),
            "away_games": len(away_games),
            "home_avg": round(home_games["points"].mean(), 1) if len(home_games) > 0 else 0,
            "away_avg": round(away_games["points"].mean(), 1) if len(away_games) > 0 else 0
        },
        "games": games
    }


@mcp.tool()
def get_player_split_stats(
    player_name: str,
    split: Literal["home_away", "rest_days"] = "home_away",
    season_start: int = 2020,
    season_end: int = 2024
) -> dict:
    """
    Get player statistics split by home/away or rest days.
    
    Args:
        player_name: Player's first name, last name, or full name
        split: Type of split - "home_away" or "rest_days"
        season_start: Starting season year (default: 2020)
        season_end: Ending season year (default: 2024)
    
    Returns:
        Dictionary with split statistics
    """
    # Find player
    player = find_player(player_name)
    if player is None:
        return {"error": f"Player '{player_name}' not found"}
    
    player_id = player["personId"]
    full_name = player["fullName"]
    
    # Convert season years to date range
    start_date = pd.Timestamp(f"{season_start}-10-01")
    end_date = pd.Timestamp(f"{season_end + 1}-09-30")
    
    # Filter player stats by date range
    stats = PLAYER_STATS_DF[
        (PLAYER_STATS_DF["personId"] == player_id) &
        (PLAYER_STATS_DF["gameDate"] >= start_date) &
        (PLAYER_STATS_DF["gameDate"] <= end_date) &
        (PLAYER_STATS_DF["minutes_decimal"] > 0) &
        (PLAYER_STATS_DF["points"].notna())
    ].copy()
    
    if stats.empty:
        return {
            "player": full_name,
            "player_id": int(player_id),
            "split_type": split,
            "season_range": f"{season_start}-{season_end}",
            "splits": [],
            "message": "No games found for this player in the specified seasons"
        }
    
    if split == "home_away":
        # Home/Away split
        home_stats = stats[stats["home"] == 1]
        away_stats = stats[stats["home"] == 0]
        
        splits = []
        for label, data in [("Home", home_stats), ("Away", away_stats)]:
            if len(data) > 0:
                splits.append({
                    "category": label,
                    "games": len(data),
                    "avg_points": round(data["points"].mean(), 1),
                    "avg_minutes": round(data["minutes_decimal"].mean(), 1),
                    "total_points": int(data["points"].sum()),
                    "fg_pct": round(
                        data["fieldGoalsMade"].sum() / data["fieldGoalsAttempted"].sum() * 100, 1
                    ) if data["fieldGoalsAttempted"].sum() > 0 else 0,
                    "three_pct": round(
                        data["threePointersMade"].sum() / data["threePointersAttempted"].sum() * 100, 1
                    ) if data["threePointersAttempted"].sum() > 0 else 0,
                    "ft_pct": round(
                        data["freeThrowsMade"].sum() / data["freeThrowsAttempted"].sum() * 100, 1
                    ) if data["freeThrowsAttempted"].sum() > 0 else 0
                })
        
        return {
            "player": full_name,
            "player_id": int(player_id),
            "split_type": "home_away",
            "season_range": f"{season_start}-{season_end}",
            "splits": splits
        }
    
    elif split == "rest_days":
        # Calculate rest days between games
        stats = stats.sort_values("gameDate")
        stats["prev_game_date"] = stats["gameDate"].shift(1)
        stats["rest_days"] = (stats["gameDate"] - stats["prev_game_date"]).dt.days - 1
        stats["rest_days"] = stats["rest_days"].fillna(0)
        
        # Categorize by rest days
        stats["rest_category"] = pd.cut(
            stats["rest_days"],
            bins=[-1, 0, 1, 2, 100],
            labels=["Back-to-back", "1 day rest", "2 days rest", "3+ days rest"]
        )
        
        splits = []
        for category in ["Back-to-back", "1 day rest", "2 days rest", "3+ days rest"]:
            data = stats[stats["rest_category"] == category]
            if len(data) > 0:
                splits.append({
                    "category": category,
                    "games": len(data),
                    "avg_points": round(data["points"].mean(), 1),
                    "avg_minutes": round(data["minutes_decimal"].mean(), 1),
                    "total_points": int(data["points"].sum()),
                    "fg_pct": round(
                        data["fieldGoalsMade"].sum() / data["fieldGoalsAttempted"].sum() * 100, 1
                    ) if data["fieldGoalsAttempted"].sum() > 0 else 0
                })
        
        return {
            "player": full_name,
            "player_id": int(player_id),
            "split_type": "rest_days",
            "season_range": f"{season_start}-{season_end}",
            "splits": splits
        }
    
    return {"error": f"Invalid split type: {split}"}


@mcp.tool()
def get_team_points_history(
    team_name: str,
    season_start: int,
    season_end: int,
    max_games: int = 82
) -> dict:
    """
    Get a team's scoring history across multiple seasons.
    
    Args:
        team_name: Team name, abbreviation, or city (e.g., "Lakers", "LAL", "Los Angeles")
        season_start: Starting season year (e.g., 2021 for 2021-22 season)
        season_end: Ending season year (e.g., 2024 for 2024-25 season)
        max_games: Maximum number of most recent games to return (default: 82)
    
    Returns:
        Dictionary with team info and game-by-game scoring data
    """
    # Find team
    team = find_team(team_name)
    if team is None:
        return {"error": f"Team '{team_name}' not found"}
    
    team_id = team["teamId"]
    full_team_name = f"{team['teamCity']} {team['teamName']}"
    
    # Convert season years to date range
    start_date = pd.Timestamp(f"{season_start}-10-01")
    end_date = pd.Timestamp(f"{season_end + 1}-09-30")
    
    # Filter team stats by team ID and date range
    stats = TEAM_STATS_DF[
        (TEAM_STATS_DF["teamId"] == team_id) &
        (TEAM_STATS_DF["gameDate"] >= start_date) &
        (TEAM_STATS_DF["gameDate"] <= end_date) &
        (TEAM_STATS_DF["teamScore"].notna())
    ].copy()
    
    if stats.empty:
        return {
            "team": full_team_name,
            "team_id": int(team_id),
            "season_range": f"{season_start}-{season_end}",
            "games": [],
            "message": "No games found for this team in the specified seasons"
        }
    
    # Sort by date and take most recent games
    stats = stats.sort_values("gameDate", ascending=False).head(max_games)
    stats = stats.sort_values("gameDate")  # Re-sort chronologically
    
    # Prepare output
    games = []
    for _, row in stats.iterrows():
        games.append({
            "date": row["gameDate"].strftime("%Y-%m-%d"),
            "points": int(row["teamScore"]),
            "opponent_points": int(row["opponentScore"]),
            "home": bool(row["home"]),
            "win": bool(row["win"]),
            "opponent": f"{row['opponentTeamCity']} {row['opponentTeamName']}",
            "field_goal_pct": round(row["fieldGoalsPercentage"], 1) if pd.notna(row["fieldGoalsPercentage"]) else 0,
            "three_point_pct": round(row["threePointersPercentage"], 1) if pd.notna(row["threePointersPercentage"]) else 0,
            "free_throw_pct": round(row["freeThrowsPercentage"], 1) if pd.notna(row["freeThrowsPercentage"]) else 0
        })
    
    # Calculate summary stats
    total_points = stats["teamScore"].sum()
    avg_points = stats["teamScore"].mean()
    home_games = stats[stats["home"] == 1]
    away_games = stats[stats["home"] == 0]
    wins = stats[stats["win"] == 1]
    
    return {
        "team": full_team_name,
        "team_id": int(team_id),
        "season_range": f"{season_start}-{season_end}",
        "total_games": len(games),
        "summary": {
            "total_points": int(total_points),
            "avg_points": round(avg_points, 1),
            "home_games": len(home_games),
            "away_games": len(away_games),
            "home_avg": round(home_games["teamScore"].mean(), 1) if len(home_games) > 0 else 0,
            "away_avg": round(away_games["teamScore"].mean(), 1) if len(away_games) > 0 else 0,
            "wins": len(wins),
            "losses": len(games) - len(wins),
            "win_pct": round(len(wins) / len(games) * 100, 1) if len(games) > 0 else 0
        },
        "games": games
    }


@mcp.tool()
def get_stat_history(
    player_name: str,
    stat: Literal["points", "rebounds", "assists", "3_pointers", "blocks"],
    num_past_games: int
) -> dict:
    """
    Get a player's statistics for a specific stat over their last N games.
    
    Args:
        player_name: Player's first name, last name, or full name
        stat: The stat to retrieve - one of: points, rebounds, assists, 3_pointers, blocks
        num_past_games: Number of most recent games to retrieve (e.g., 10, 20, 82)
    
    Returns:
        Dictionary with player info and game-by-game stat data
    """
    # Find player
    player = find_player(player_name)
    if player is None:
        return {"error": f"Player '{player_name}' not found"}
    
    player_id = player["personId"]
    full_name = player["fullName"]
    
    # Map stat parameter to DataFrame column name
    stat_column_map = {
        "points": "points",
        "rebounds": "reboundsTotal",
        "assists": "assists",
        "3_pointers": "threePointersMade",
        "blocks": "blocks"
    }
    
    stat_column = stat_column_map[stat]
    
    # Filter player stats (get all games for this player with valid data)
    stats = PLAYER_STATS_DF[
        (PLAYER_STATS_DF["personId"] == player_id) &
        (PLAYER_STATS_DF["minutes_decimal"] > 0) &
        (PLAYER_STATS_DF[stat_column].notna())
    ].copy()
    
    if stats.empty:
        return {
            "player": full_name,
            "player_id": int(player_id),
            "stat": stat,
            "games": [],
            "message": "No games found for this player"
        }
    
    # Sort by date (most recent first) and take the requested number of games
    stats = stats.sort_values("gameDate", ascending=False).head(num_past_games)
    # Re-sort chronologically for display
    stats = stats.sort_values("gameDate")
    
    # Prepare output
    games = []
    for _, row in stats.iterrows():
        game_data = {
            "date": row["gameDate"].strftime("%Y-%m-%d"),
            "season": int(row["season"]),
            "stat_value": int(row[stat_column]),
            "minutes": round(row["minutes_decimal"], 1),
            "home": bool(row["home"])
        }
        
        # Add additional context based on stat type
        if stat == "points":
            game_data["field_goals"] = f"{int(row['fieldGoalsMade'])}/{int(row['fieldGoalsAttempted'])}"
            game_data["free_throws"] = f"{int(row['freeThrowsMade'])}/{int(row['freeThrowsAttempted'])}"
        elif stat == "rebounds":
            game_data["offensive_rebounds"] = int(row["reboundsOffensive"])
            game_data["defensive_rebounds"] = int(row["reboundsDefensive"])
        elif stat == "3_pointers":
            game_data["three_point_attempts"] = int(row["threePointersAttempted"])
            game_data["three_point_pct"] = round(
                (row["threePointersMade"] / row["threePointersAttempted"] * 100), 1
            ) if row["threePointersAttempted"] > 0 else 0
        
        games.append(game_data)
    
    # Calculate summary stats
    stat_values = stats[stat_column]
    total_stat = stat_values.sum()
    avg_stat = stat_values.mean()
    max_stat = stat_values.max()
    min_stat = stat_values.min()
    
    return {
        "player": full_name,
        "player_id": int(player_id),
        "stat": stat,
        "num_games_requested": num_past_games,
        "num_games_returned": len(games),
        "summary": {
            "total": int(total_stat),
            "average": round(avg_stat, 1),
            "max": int(max_stat),
            "min": int(min_stat),
            "avg_minutes": round(stats["minutes_decimal"].mean(), 1)
        },
        "games": games
    }


# Load data when server starts
load_data()


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
