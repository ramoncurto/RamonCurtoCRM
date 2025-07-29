#!/usr/bin/env python3
"""
GPT-4o-mini Risk Analysis Module

This module uses GPT-4o-mini to analyze athlete conversations and highlights
for risk factors, providing more nuanced and language-agnostic analysis.
"""

import os
import json
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

class GPTRiskAnalyzer:
    """GPT-4o-mini based risk analyzer for athlete conversations."""
    
    def __init__(self, openai_client: AsyncOpenAI):
        self.client = openai_client
        
        # Risk analysis prompts
        self.risk_prompts = {
            'sentiment': """
Analiza el sentimiento y tono emocional del siguiente texto de un atleta.
Responde solo con un número entre -1 y +1 donde:
- -1 = muy negativo (frustrado, deprimido, estresado)
- 0 = neutral
- +1 = muy positivo (motivado, feliz, progresando)

Texto: {text}

Respuesta (solo número):""",

            'pain_injury': """
Identifica menciones de dolor, lesiones, molestias físicas o problemas de salud en el siguiente texto.
Responde solo con un número entre 0 y 1 donde:
- 0 = no hay menciones de dolor/lesión
- 0.3 = mención leve (molestia, cansancio)
- 0.7 = mención moderada (dolor, lesión menor)
- 1.0 = mención grave (lesión seria, dolor intenso)

Texto: {text}

Respuesta (solo número):""",

            'sleep_fatigue': """
Identifica problemas de sueño, fatiga, cansancio o problemas de descanso en el siguiente texto.
Responde solo con un número entre 0 y 1 donde:
- 0 = no hay menciones de problemas de sueño
- 0.3 = mención leve (cansado, poco descanso)
- 0.7 = mención moderada (problemas de sueño, insomnio)
- 1.0 = mención grave (no duerme, fatiga extrema)

Texto: {text}

Respuesta (solo número):""",

            'motivation_psychology': """
Evalúa el estado psicológico y motivacional del atleta en el siguiente texto.
Responde solo con un número entre -1 y +1 donde:
- -1 = muy negativo (desmotivado, deprimido, ansioso)
- 0 = neutral
- +1 = muy positivo (motivado, confiado, progresando)

Texto: {text}

Respuesta (solo número):""",

            'compliance_adherence': """
Evalúa la adherencia y cumplimiento del atleta con sus planes de entrenamiento.
Responde solo con un número entre 0 y 1 donde:
- 0 = no hay información sobre cumplimiento
- 0.3 = cumplimiento parcial o dudas
- 0.7 = cumplimiento bueno con algunos problemas
- 1.0 = cumplimiento excelente

Texto: {text}

Respuesta (solo número):"""
        }
    
    async def analyze_conversation_sentiment(self, transcription: str, response: str) -> float:
        """Analyze sentiment of a conversation using GPT-4o-mini."""
        try:
            combined_text = f"Athlete: {transcription}\nCoach: {response}"
            
            prompt = self.risk_prompts['sentiment'].format(text=combined_text)
            
            completion = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10,
                temperature=0.1
            )
            
            result = completion.choices[0].message.content.strip()
            
            # Parse numeric response
            try:
                sentiment = float(result)
                return max(-1.0, min(1.0, sentiment))  # Clamp to [-1, 1]
            except ValueError:
                logger.warning(f"Could not parse sentiment result: {result}")
                return 0.0
                
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return 0.0
    
    async def analyze_pain_injury_mentions(self, text: str) -> float:
        """Analyze pain/injury mentions using GPT-4o-mini."""
        try:
            prompt = self.risk_prompts['pain_injury'].format(text=text)
            
            completion = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10,
                temperature=0.1
            )
            
            result = completion.choices[0].message.content.strip()
            
            try:
                score = float(result)
                return max(0.0, min(1.0, score))  # Clamp to [0, 1]
            except ValueError:
                logger.warning(f"Could not parse pain/injury result: {result}")
                return 0.0
                
        except Exception as e:
            logger.error(f"Error analyzing pain/injury: {e}")
            return 0.0
    
    async def analyze_sleep_fatigue(self, text: str) -> float:
        """Analyze sleep/fatigue mentions using GPT-4o-mini."""
        try:
            prompt = self.risk_prompts['sleep_fatigue'].format(text=text)
            
            completion = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10,
                temperature=0.1
            )
            
            result = completion.choices[0].message.content.strip()
            
            try:
                score = float(result)
                return max(0.0, min(1.0, score))  # Clamp to [0, 1]
            except ValueError:
                logger.warning(f"Could not parse sleep/fatigue result: {result}")
                return 0.0
                
        except Exception as e:
            logger.error(f"Error analyzing sleep/fatigue: {e}")
            return 0.0
    
    async def analyze_motivation_psychology(self, text: str) -> float:
        """Analyze motivation and psychological state using GPT-4o-mini."""
        try:
            prompt = self.risk_prompts['motivation_psychology'].format(text=text)
            
            completion = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10,
                temperature=0.1
            )
            
            result = completion.choices[0].message.content.strip()
            
            try:
                score = float(result)
                return max(-1.0, min(1.0, score))  # Clamp to [-1, 1]
            except ValueError:
                logger.warning(f"Could not parse motivation result: {result}")
                return 0.0
                
        except Exception as e:
            logger.error(f"Error analyzing motivation: {e}")
            return 0.0
    
    async def analyze_compliance_adherence(self, text: str) -> float:
        """Analyze compliance and adherence to training plans using GPT-4o-mini."""
        try:
            prompt = self.risk_prompts['compliance_adherence'].format(text=text)
            
            completion = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10,
                temperature=0.1
            )
            
            result = completion.choices[0].message.content.strip()
            
            try:
                score = float(result)
                return max(0.0, min(1.0, score))  # Clamp to [0, 1]
            except ValueError:
                logger.warning(f"Could not parse compliance result: {result}")
                return 0.0
                
        except Exception as e:
            logger.error(f"Error analyzing compliance: {e}")
            return 0.0
    
    async def analyze_conversation_batch(self, conversations: List[Tuple[str, str]]) -> Dict[str, List[float]]:
        """Analyze a batch of conversations for all risk factors."""
        results = {
            'sentiment': [],
            'pain_injury': [],
            'sleep_fatigue': [],
            'motivation_psychology': [],
            'compliance_adherence': []
        }
        
        for transcription, response in conversations:
            # Analyze sentiment
            sentiment = await self.analyze_conversation_sentiment(transcription, response)
            results['sentiment'].append(sentiment)
            
            # Combine text for other analyses
            combined_text = f"{transcription} {response}"
            
            # Analyze other factors
            pain_score = await self.analyze_pain_injury_mentions(combined_text)
            results['pain_injury'].append(pain_score)
            
            sleep_score = await self.analyze_sleep_fatigue(combined_text)
            results['sleep_fatigue'].append(sleep_score)
            
            motivation_score = await self.analyze_motivation_psychology(combined_text)
            results['motivation_psychology'].append(motivation_score)
            
            compliance_score = await self.analyze_compliance_adherence(combined_text)
            results['compliance_adherence'].append(compliance_score)
        
        return results
    
    async def analyze_highlights(self, highlights: List[str]) -> Dict[str, float]:
        """Analyze athlete highlights for risk factors."""
        if not highlights:
            return {
                'negative_ratio': 0.0,
                'pain_injury_ratio': 0.0,
                'sleep_fatigue_ratio': 0.0,
                'motivation_psychology_avg': 0.0
            }
        
        # Analyze each highlight
        pain_scores = []
        sleep_scores = []
        motivation_scores = []
        
        for highlight in highlights:
            pain_score = await self.analyze_pain_injury_mentions(highlight)
            pain_scores.append(pain_score)
            
            sleep_score = await self.analyze_sleep_fatigue(highlight)
            sleep_scores.append(sleep_score)
            
            motivation_score = await self.analyze_motivation_psychology(highlight)
            motivation_scores.append(motivation_score)
        
        # Calculate ratios and averages
        total_highlights = len(highlights)
        
        return {
            'negative_ratio': sum(1 for s in motivation_scores if s < -0.3) / total_highlights,
            'pain_injury_ratio': sum(1 for s in pain_scores if s > 0.3) / total_highlights,
            'sleep_fatigue_ratio': sum(1 for s in sleep_scores if s > 0.3) / total_highlights,
            'motivation_psychology_avg': sum(motivation_scores) / total_highlights
        }

# Example usage
async def test_gpt_analysis():
    """Test the GPT-based risk analysis."""
    from dotenv import load_dotenv
    load_dotenv()
    
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    analyzer = GPTRiskAnalyzer(client)
    
    # Test conversation analysis
    test_conversations = [
        ("Me duele la rodilla desde ayer", "¿Cuándo empezó el dolor?"),
        ("No puedo dormir bien, estoy muy estresado", "Entiendo, vamos a trabajar en eso"),
        ("¡Hoy corrí 10km sin problemas!", "¡Excelente progreso!")
    ]
    
    print("🧪 Testing GPT-based risk analysis...")
    
    results = await analyzer.analyze_conversation_batch(test_conversations)
    
    print("Results:")
    for factor, scores in results.items():
        print(f"  {factor}: {scores}")
    
    # Test highlights analysis
    test_highlights = [
        "Menciona dolor en la rodilla durante el entrenamiento",
        "Problemas de sueño, duerme solo 4 horas",
        "Muy motivado, completó todos los ejercicios"
    ]
    
    highlight_results = await analyzer.analyze_highlights(test_highlights)
    
    print("\nHighlight Analysis:")
    for factor, score in highlight_results.items():
        print(f"  {factor}: {score:.3f}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_gpt_analysis())