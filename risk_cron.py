#!/usr/bin/env python3
"""
Daily Risk Radar Recalculation Cron Job

This script runs daily at 5:00 AM Europe/Madrid time to recalculate
risk scores for all athletes and save them to the history table.

Usage:
    python risk_cron.py

Or schedule with cron:
    0 5 * * * /path/to/python /path/to/risk_cron.py
"""

import os
import sys
import sqlite3
import json
import logging
from datetime import datetime
import math

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the risk calculation functions from main.py
from main import get_athlete_risk_factors, RISK_WEIGHTS, RISK_KEYWORDS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('risk_cron.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_daily_risk_recalculation():
    """Run daily risk recalculation for all athletes."""
    try:
        # Connect to database
        db_path = 'database.db'
        conn = sqlite3.connect(db_path)
        
        logger.info("Starting daily risk recalculation...")
        
        # Get all athletes
        cursor = conn.execute("SELECT id, name FROM athletes")
        athletes = cursor.fetchall()
        
        logger.info(f"Found {len(athletes)} athletes to process")
        
        results = []
        total_processed = 0
        errors = 0
        
        for athlete in athletes:
            athlete_id = athlete[0]
            athlete_name = athlete[1]
            
            try:
                # Calculate risk factors
                risk_data = get_athlete_risk_factors(athlete_id)
                
                if risk_data:
                    # Save to history
                    conn.execute("""
                        INSERT INTO athlete_risk_history 
                        (athlete_id, score, level, factors_json) 
                        VALUES (?, ?, ?, ?)
                    """, (
                        athlete_id,
                        risk_data['score'],
                        risk_data['level'],
                        json.dumps(risk_data['factors'])
                    ))
                    
                    results.append({
                        'athlete_id': athlete_id,
                        'athlete_name': athlete_name,
                        'score': risk_data['score'],
                        'level': risk_data['level'],
                        'color': risk_data['color']
                    })
                    
                    total_processed += 1
                    logger.info(f"Processed {athlete_name} (ID: {athlete_id}) - Score: {risk_data['score']}, Level: {risk_data['level']}")
                    
                else:
                    logger.warning(f"No risk data returned for athlete {athlete_id} ({athlete_name})")
                    errors += 1
                    
            except Exception as e:
                logger.error(f"Error processing athlete {athlete_id} ({athlete_name}): {e}")
                errors += 1
        
        conn.commit()
        conn.close()
        
        # Log summary
        logger.info(f"Daily risk recalculation completed:")
        logger.info(f"  - Total athletes: {len(athletes)}")
        logger.info(f"  - Successfully processed: {total_processed}")
        logger.info(f"  - Errors: {errors}")
        
        # Log high-risk athletes
        high_risk = [r for r in results if r['level'] in ['rojo', 'alto']]
        if high_risk:
            logger.warning(f"High-risk athletes detected ({len(high_risk)}):")
            for athlete in high_risk:
                logger.warning(f"  - {athlete['athlete_name']} (Score: {athlete['score']}, Level: {athlete['level']})")
        
        return {
            'status': 'success',
            'total_athletes': len(athletes),
            'processed': total_processed,
            'errors': errors,
            'high_risk_count': len(high_risk),
            'results': results
        }
        
    except Exception as e:
        logger.error(f"Critical error in daily risk recalculation: {e}")
        return {
            'status': 'error',
            'message': str(e)
        }

def main():
    """Main function to run the cron job."""
    logger.info("Risk Radar Cron Job Started")
    
    result = run_daily_risk_recalculation()
    
    if result['status'] == 'success':
        logger.info("Risk Radar Cron Job Completed Successfully")
        sys.exit(0)
    else:
        logger.error("Risk Radar Cron Job Failed")
        sys.exit(1)

if __name__ == "__main__":
    main()