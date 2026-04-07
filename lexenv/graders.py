"""
Graders for LexEnv
- Fuzzy keyword matching to identify issues in agent analysis
- Per-step and episode scoring
- Reward shaping for partial progress
"""

from typing import List, Dict, Any, Set, Tuple
from difflib import SequenceMatcher
import re


class LexGrader:
    """Grader for legal document analysis tasks"""
    
    def __init__(self, ground_truth: List[Dict[str, Any]]):
        """
        Args:
            ground_truth: List of issue dicts with 'keywords' and 'weight' keys
        """
        self.ground_truth = ground_truth
        self.total_weight = sum(issue["weight"] for issue in ground_truth)
    
    def extract_keywords_from_text(self, text: str) -> Set[str]:
        """Extract key phrases and keywords from analysis text"""
        # Lowercase and tokenize
        text_lower = text.lower()
        
        # Extract phrases (sequences of 2-4 words)
        words = re.findall(r'\b[a-z]+\b', text_lower)
        phrases = set()
        
        # Add individual keywords
        phrases.update(words)
        
        # Add bigrams and trigrams
        for i in range(len(words) - 1):
            phrases.add(f"{words[i]} {words[i+1]}")
        for i in range(len(words) - 2):
            phrases.add(f"{words[i]} {words[i+1]} {words[i+2]}")
        
        return phrases
    
    def fuzzy_match(self, agent_text: str, issue_keywords: List[str], threshold: float = 0.6) -> float:
        """
        Calculate fuzzy match score between agent analysis and issue keywords
        
        Returns match confidence (0.0 - 1.0)
        """
        if not agent_text or not issue_keywords:
            return 0.0
        
        agent_text_lower = agent_text.lower()
        max_match = 0.0
        
        for keyword in issue_keywords:
            keyword_lower = keyword.lower()
            
            # Exact substring match (highest confidence)
            if keyword_lower in agent_text_lower:
                return 1.0
            
            # Fuzzy similarity
            ratio = SequenceMatcher(None, agent_text_lower, keyword_lower).ratio()
            max_match = max(max_match, ratio)
            
            # Try word-level matching
            agent_words = set(re.findall(r'\b\w+\b', agent_text_lower))
            keyword_words = set(re.findall(r'\b\w+\b', keyword_lower))
            
            if keyword_words and agent_words:
                overlap = len(keyword_words & agent_words) / len(keyword_words)
                max_match = max(max_match, overlap)
        
        return min(1.0, max_match) if max_match >= threshold else max_match * 0.5
    
    def grade_step(self, agent_analysis: str, agent_risk_level: str) -> Tuple[float, List[int], List[float]]:
        """
        Grade a single step of analysis
        
        Returns:
            - step_score: 0.0-1.0 score for this step
            - matched_issue_ids: which issues were identified
            - match_confidences: confidence for each match
        """
        step_score = 0.0
        matched_issue_ids = []
        match_confidences = []
        
        if not agent_analysis or len(agent_analysis.strip()) < 50:
            # Penalty for too-short analysis
            return max(0.0, -0.05), [], []
        
        for issue in self.ground_truth:
            keywords = issue.get("keywords", [])
            confidence = self.fuzzy_match(agent_analysis, keywords)
            
            if confidence > 0.5:  # Issue appears to be identified
                matched_issue_ids.append(issue["id"])
                match_confidences.append(confidence)
                
                # Add weighted score for this issue
                step_score += issue.get("weight", 1.0/len(self.ground_truth)) * confidence
        
        return min(1.0, step_score), matched_issue_ids, match_confidences
    
    def grade_episode(
        self,
        all_analyses: List[str],
        all_risk_levels: List[str],
        steps_taken: int
    ) -> Dict[str, float]:
        """
        Grade entire episode across multiple steps
        
        Returns dict with:
            - completeness: how many issues found
            - accuracy: penalties for false understanding
            - efficiency: bonus for quick identification
            - final_score: overall 0.0-1.0 score
        """
        # Combine all analyses
        combined_analysis = "\n".join(all_analyses)
        
        # Check which issues were found
        identified_issues = set()
        total_confidence = 0.0
        
        for issue in self.ground_truth:
            keywords = issue.get("keywords", [])
            confidence = self.fuzzy_match(combined_analysis, keywords)
            
            if confidence > 0.5:
                identified_issues.add(issue["id"])
                total_confidence += confidence
        
        # Completeness score (% of issues found)
        completeness = len(identified_issues) / len(self.ground_truth) if self.ground_truth else 1.0
        
        # Accuracy: penalize if very few high-confidence matches
        if identified_issues:
            accuracy = min(1.0, max(0.5, total_confidence / len(identified_issues)))
        else:
            accuracy = 0.0
        
        # Efficiency: bonus if found enough issues in few steps
        expected_steps = max(2, len(self.ground_truth) / 3)  # ~3 issues per step
        efficiency = min(1.0, max(0.5, expected_steps / steps_taken))
        
        # Final weighted score
        final_score = (0.60 * completeness) + (0.25 * accuracy) + (0.15 * efficiency)
        
        return {
            "completeness": completeness,
            "accuracy": accuracy,
            "efficiency": efficiency,
            "final_score": min(1.0, max(0.0, final_score))
        }
    
    def calculate_step_reward(
        self,
        agent_analysis: str,
        agent_risk_level: str,
        step_num: int,
        is_final_step: bool = False
    ) -> Dict[str, float]:
        """
        Calculate detailed reward for a single step
        
        Returns breakdown:
            - per_step_score: base score from issue identification
            - efficiency_bonus: early step bonus
            - analysis_quality: text quality bonus
            - risk_match_bonus: if risk level assessment is reasonable
            - total_reward: final step reward
        """
        # Base score from issue identification
        step_score, _, confidences = self.grade_step(agent_analysis, agent_risk_level)
        
        # Early step bonus (more reward for finding issues quickly)
        early_bonus = max(0.0, (1.0 - step_num / 5) * 0.05)
        
        # Analysis quality bonus (longer, more detailed analysis)
        text_len = len(agent_analysis.strip())
        quality_bonus = min(0.05, text_len / 1000 * 0.05) if text_len > 50 else -0.05
        
        # Risk assessment alignment (basic check - just ensure it's not clearly wrong)
        risk_match = 0.0
        if agent_risk_level.lower() in ["low", "medium", "high", "critical"]:
            # Higher confidence if risk level seems reasonable
            num_issues = len([x for x in confidences if x > 0.5])
            if agent_risk_level.lower() == "critical" and num_issues >= 2:
                risk_match = 0.05
            elif agent_risk_level.lower() == "high" and num_issues >= 1:
                risk_match = 0.05
        
        total_reward = max(0.0, min(1.0, step_score + early_bonus + quality_bonus + risk_match))
        
        return {
            "per_step_score": step_score,
            "efficiency_bonus": early_bonus,
            "analysis_quality": quality_bonus,
            "risk_match_bonus": risk_match,
            "false_positive_penalty": 0.0,
            "total_step_reward": total_reward
        }


def create_grader_for_task(task_id: str, ground_truth: List[Dict[str, Any]]) -> LexGrader:
    """Factory function to create grader for specific task"""
    return LexGrader(ground_truth)
