import numpy as np
import pandas as pd
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class DataDrivenDominanceQuotientCalculator:
    def __init__(self):
        """
        Dominance Quotient calculator based on BLCS4 season analysis
        Designed to identify individual skill regardless of team performance
        """
        
        # Weights based on BLCS4 data analysis
        # Key insight: Individual stats matter WAY more than team success
        self.stat_weights = {
            # Core individual performance (90% total weight)
            'avg_score': 0.40,              # Most important - overall game impact
            'saves_per_game': 0.25,         # Defensive skill highly valued (who Drose had 2.45!)
            'goals_per_game': 0.15,         # Offensive production
            'assists_per_game': 0.10,       # Playmaking/team support
            
            # Secondary performance indicators (5% total weight)
            'shooting_pct': 0.03,           # Efficiency over volume
            'shots_per_game': 0.02,         # Offensive pressure
            
            # Team success (5% total weight) - MINIMAL impact
            'win_rate': 0.05                # Proven to be mostly team luck
        }
        
        # Tournament adjustments based on Bo7 double elimination
        self.tournament_config = {
            'min_games_threshold': 8,        # Minimum possible games (0-4, 0-4)
            'early_elimination_threshold': 14,  # 8-14 games = early out
            'deep_run_threshold': 22,        # 22+ games = finals/winner
            'confidence_games': 16,          # Games needed for full win rate confidence
            
            # Opportunity adjustments
            'early_elimination_boost': 0.12,  # 12% boost for early elimination
            'deep_run_penalty': 0.06,        # 6% penalty for deep runs
        }
        
        # Performance thresholds based on BLCS4 data
        self.performance_benchmarks = {
            'elite_score_threshold': 450,     # Top tier like JERID (543), DESI (488)
            'good_score_threshold': 380,      # Above average performers
            'average_score_threshold': 320,   # League average range
            
            'elite_saves_threshold': 2.2,     # Defensive specialists like who Drose (2.45)
            'good_saves_threshold': 1.8,      # Above average defense
            
            'elite_goals_threshold': 1.1,     # Offensive threats like JERID (1.16)
            'good_goals_threshold': 0.8,      # Above average offense
        }
    
    def calculate_percentile(self, player_value: float, all_values: List[float], 
                           higher_is_better: bool = True) -> float:
        """Calculate what percentage of players this value beats"""
        if not all_values or len(all_values) <= 1:
            return 50.0
        
        # Filter out invalid values
        valid_values = [v for v in all_values if not pd.isna(v) and v is not None]
        if not valid_values:
            return 50.0
        
        if higher_is_better:
            better_count = sum(1 for v in valid_values if v < player_value)
        else:
            better_count = sum(1 for v in valid_values if v > player_value)
        
        return (better_count / len(valid_values)) * 100
    
    def get_tournament_adjustment_factor(self, games_played: int) -> float:
        """Calculate opportunity adjustment based on games played"""
        if games_played <= self.tournament_config['early_elimination_threshold']:
            # Early elimination: Fewer opportunities to showcase skill
            adjustment = 1.0 + self.tournament_config['early_elimination_boost']
            adjustment_type = "early elimination boost"
        elif games_played >= self.tournament_config['deep_run_threshold']:
            # Deep run: More opportunities to accumulate stats
            adjustment = 1.0 - self.tournament_config['deep_run_penalty']
            adjustment_type = "deep run penalty"
        else:
            # Standard tournament run
            adjustment = 1.0
            adjustment_type = "no adjustment"
        
        logger.info(f"Games: {games_played}, adjustment: {adjustment:.3f} ({adjustment_type})")
        return adjustment
    
    def calculate_skill_consistency_bonus(self, player_stats: Dict) -> float:
        """Bonus for players who excel in multiple areas (like JERID, DESI)"""
        score_tier = 0
        if player_stats.get('avg_score', 0) >= self.performance_benchmarks['elite_score_threshold']:
            score_tier = 3  # Elite
        elif player_stats.get('avg_score', 0) >= self.performance_benchmarks['good_score_threshold']:
            score_tier = 2  # Good
        elif player_stats.get('avg_score', 0) >= self.performance_benchmarks['average_score_threshold']:
            score_tier = 1  # Average
        
        # Check if player excels in multiple specific areas
        specialties = 0
        if player_stats.get('saves_per_game', 0) >= self.performance_benchmarks['elite_saves_threshold']:
            specialties += 1  # Defensive specialist
        if player_stats.get('goals_per_game', 0) >= self.performance_benchmarks['elite_goals_threshold']:
            specialties += 1  # Offensive threat
        if player_stats.get('assists_per_game', 0) >= 1.0:
            specialties += 1  # Playmaker
        
        # Multi-skilled players get a small bonus
        if score_tier >= 2 and specialties >= 2:
            return 1.05  # 5% bonus for well-rounded elite players
        elif score_tier >= 1 and specialties >= 1:
            return 1.02  # 2% bonus for solid specialists
        else:
            return 1.0   # No bonus
    
    def calculate_win_rate_with_context(self, player_stats: Dict, all_players: List[Dict]) -> float:
        """Calculate win rate percentile with heavy regression for small samples"""
        player_games = player_stats.get('games_played', 0)
        player_wins = player_stats.get('wins', 0)
        player_win_rate = player_wins / max(player_games, 1)
        
        # Calculate league averages
        total_wins = sum(p.get('wins', 0) for p in all_players)
        total_games = sum(p.get('games_played', 0) for p in all_players)
        league_avg_win_rate = total_wins / max(total_games, 1)
        
        # Heavy regression to mean for tournament play
        confidence_factor = min(player_games / self.tournament_config['confidence_games'], 1.0)
        
        # Blend individual win rate with league average
        adjusted_win_rate = (confidence_factor * player_win_rate) + \
                           ((1 - confidence_factor) * league_avg_win_rate)
        
        # Calculate percentile among all adjusted win rates
        all_adjusted_rates = []
        for p in all_players:
            p_games = p.get('games_played', 0)
            p_wins = p.get('wins', 0)
            p_win_rate = p_wins / max(p_games, 1)
            p_confidence = min(p_games / self.tournament_config['confidence_games'], 1.0)
            p_adjusted = (p_confidence * p_win_rate) + ((1 - p_confidence) * league_avg_win_rate)
            all_adjusted_rates.append(p_adjusted)
        
        percentile = self.calculate_percentile(adjusted_win_rate, all_adjusted_rates, True)
        
        logger.info(f"Win rate: {player_win_rate:.3f} → {adjusted_win_rate:.3f} "
                   f"(confidence: {confidence_factor:.2f}, percentile: {percentile:.1f})")
        
        return percentile
    
    def calculate_dominance_quotient(self, player_stats: Dict, all_players: List[Dict]) -> float:
        """
        Calculate the Data-Driven Dominance Quotient
        Based on BLCS4 analysis showing individual stats >> team success
        """
        if not all_players:
            return 50.0
        
        player_name = player_stats.get('player_id', 'Unknown')
        logger.info(f"\n=== Calculating DQ for {player_name} ===")
        
        # Extract stat values for percentile calculations
        stat_lists = {}
        for stat_key in ['avg_score', 'goals_per_game', 'assists_per_game', 'saves_per_game', 
                        'shots_per_game', 'shooting_pct']:
            stat_lists[stat_key] = [p.get(stat_key, 0) for p in all_players if p.get(stat_key) is not None]
        
        # Calculate percentiles for each stat
        percentiles = {}
        weighted_contributions = {}
        
        for stat_key, weight in self.stat_weights.items():
            if stat_key == 'win_rate':
                # Special handling for win rate
                percentiles[stat_key] = self.calculate_win_rate_with_context(player_stats, all_players)
            elif stat_key in stat_lists and stat_lists[stat_key]:
                player_value = player_stats.get(stat_key, 0)
                percentiles[stat_key] = self.calculate_percentile(player_value, stat_lists[stat_key], True)
            else:
                percentiles[stat_key] = 50.0  # Default if no data
            
            # Calculate weighted contribution
            weighted_contributions[stat_key] = percentiles[stat_key] * weight
            
            logger.info(f"{stat_key}: {player_stats.get(stat_key, 0):.2f} → "
                       f"{percentiles[stat_key]:.1f}th percentile × {weight:.3f} = "
                       f"{weighted_contributions[stat_key]:.2f}")
        
        # Sum all weighted contributions
        base_dominance_quotient = sum(weighted_contributions.values())
        
        # Apply tournament opportunity adjustment
        games_played = player_stats.get('games_played', 0)
        tournament_factor = self.get_tournament_adjustment_factor(games_played)
        
        # Apply skill consistency bonus
        consistency_bonus = self.calculate_skill_consistency_bonus(player_stats)
        
        # Calculate final DQ
        final_dq = base_dominance_quotient * tournament_factor * consistency_bonus
        
        # Clamp to 0-100 range
        final_dq = max(0, min(100, final_dq))
        
        logger.info(f"Base DQ: {base_dominance_quotient:.2f}")
        logger.info(f"Tournament factor: {tournament_factor:.3f}")
        logger.info(f"Consistency bonus: {consistency_bonus:.3f}")
        logger.info(f"Final DQ: {final_dq:.1f}")
        
        return final_dq
    
    def analyze_player_profile(self, player_stats: Dict, all_players: List[Dict]) -> Dict:
        """Provide detailed analysis of a player's strengths and weaknesses"""
        analysis = {
            'dominance_quotient': self.calculate_dominance_quotient(player_stats, all_players),
            'player_type': '',
            'strengths': [],
            'weaknesses': [],
            'comparison_to_league': {}
        }
        
        # Determine player type based on stats
        avg_score = player_stats.get('avg_score', 0)
        saves_per_game = player_stats.get('saves_per_game', 0)
        goals_per_game = player_stats.get('goals_per_game', 0)
        win_rate = player_stats.get('wins', 0) / max(player_stats.get('games_played', 1), 1) * 100
        
        # Player type classification
        if avg_score >= self.performance_benchmarks['elite_score_threshold']:
            if win_rate >= 55:
                analysis['player_type'] = "Elite Carry (High skill + winning team)"
            else:
                analysis['player_type'] = "Elite Victim (High skill + bad team)"
        elif avg_score >= self.performance_benchmarks['good_score_threshold']:
            analysis['player_type'] = "Solid Contributor"
        elif win_rate >= 55:
            analysis['player_type'] = "Team Passenger (Carried by good team)"
        else:
            analysis['player_type'] = "Developing Player"
        
        # Identify strengths
        if saves_per_game >= self.performance_benchmarks['elite_saves_threshold']:
            analysis['strengths'].append("Elite Defender")
        if goals_per_game >= self.performance_benchmarks['elite_goals_threshold']:
            analysis['strengths'].append("Offensive Threat")
        if player_stats.get('assists_per_game', 0) >= 1.0:
            analysis['strengths'].append("Playmaker")
        if avg_score >= self.performance_benchmarks['elite_score_threshold']:
            analysis['strengths'].append("Overall Impact")
        
        return analysis

# Integration with existing bot system
class DataDrivenBLCSXBot(BLCSXBot):
    def __init__(self, db_config: Dict, ballchasing_token: str):
        super().__init__(db_config, ballchasing_token)
        # Replace calculator with data-driven version
        self.calculator = DataDrivenDominanceQuotientCalculator()
        logger.info("Initialized with data-driven dominance quotient calculator based on BLCS4 analysis")

# Test function with BLCS4-style data
def test_data_driven_algorithm():
    """Test the new algorithm with players similar to BLCS4 patterns"""
    
    # Test data based on BLCS4 patterns
    test_players = [
        # Elite player on winning team (like JERID, DESI)
        {
            'player_id': 'Elite_Winner', 'games_played': 24, 'wins': 18, 'losses': 6,
            'avg_score': 520, 'goals_per_game': 1.2, 'assists_per_game': 1.1,
            'saves_per_game': 2.1, 'shots_per_game': 4.5, 'shooting_pct': 27
        },
        
        # Elite player on bad team (like who Drose, Paperclip94)
        {
            'player_id': 'Elite_Victim', 'games_played': 12, 'wins': 3, 'losses': 9,
            'avg_score': 480, 'goals_per_game': 1.0, 'assists_per_game': 1.3,
            'saves_per_game': 2.8, 'shots_per_game': 4.8, 'shooting_pct': 21
        },
        
        # Average player on good team (like bacon, Pullis)
        {
            'player_id': 'Team_Passenger', 'games_played': 22, 'wins': 16, 'losses': 6,
            'avg_score': 310, 'goals_per_game': 0.7, 'assists_per_game': 0.6,
            'saves_per_game': 1.2, 'shots_per_game': 3.2, 'shooting_pct': 22
        },
        
        # Poor player on bad team
        {
            'player_id': 'Struggling', 'games_played': 14, 'wins': 4, 'losses': 10,
            'avg_score': 280, 'goals_per_game': 0.5, 'assists_per_game': 0.4,
            'saves_per_game': 1.0, 'shots_per_game': 2.8, 'shooting_pct': 18
        },
        
        # Defensive specialist (like who Drose defensive style)
        {
            'player_id': 'Defense_Specialist', 'games_played': 16, 'wins': 6, 'losses': 10,
            'avg_score': 400, 'goals_per_game': 0.6, 'assists_per_game': 0.9,
            'saves_per_game': 3.2, 'shots_per_game': 2.9, 'shooting_pct': 21
        }
    ]
    
    calc = DataDrivenDominanceQuotientCalculator()
    
    print("=== DATA-DRIVEN ALGORITHM TEST ===")
    print("Based on BLCS4 analysis: Individual skill >> Team success")
    print()
    
    results = []
    for player in test_players:
        dq = calc.calculate_dominance_quotient(player, test_players)
        analysis = calc.analyze_player_profile(player, test_players)
        results.append((player['player_id'], dq, analysis, player))
    
    # Sort by DQ
    results.sort(key=lambda x: x[1], reverse=True)
    
    print("Expected ranking: Elite players (Winner & Victim) at top, regardless of team success")
    print()
    
    for i, (name, dq, analysis, stats) in enumerate(results, 1):
        win_rate = stats['wins'] / stats['games_played'] * 100
        print(f"#{i} {name}: {dq:.1f}% DQ")
        print(f"    Type: {analysis['player_type']}")
        print(f"    Stats: {stats['avg_score']:.0f} score, {stats['goals_per_game']:.1f} goals, {stats['saves_per_game']:.1f} saves")
        print(f"    Record: {stats['games_played']} games, {win_rate:.0f}% WR")
        if analysis['strengths']:
            print(f"    Strengths: {', '.join(analysis['strengths'])}")
        print()

if __name__ == "__main__":
    test_data_driven_algorithm()
