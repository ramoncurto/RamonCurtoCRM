# Athlete Highlights Guide

This guide explains how to use the new athlete highlights functionality in the Ramon CRM system.

## Overview

The athlete highlights feature allows you to create and manage key points or summaries from athlete conversations. These highlights serve as quick reference points for important information discussed with each athlete.

## Database Schema

The highlights are stored in the `athlete_highlights` table with the following structure:

- `id`: Primary key
- `athlete_id`: Foreign key to athletes table
- `highlight_text`: The key point or summary text
- `category`: Category of the highlight (training, nutrition, recovery, goals, etc.)
- `source_conversation_id`: Optional link to the original conversation
- `created_at`: Timestamp when created
- `updated_at`: Timestamp when last updated
- `is_active`: Boolean flag to enable/disable highlights

## API Endpoints

### 1. Create a Highlight
**POST** `/athletes/{athlete_id}/highlights`

**Parameters:**
- `highlight_text` (required): The key point to highlight
- `category` (optional): Category of the highlight (default: "general")
- `source_conversation_id` (optional): Link to source conversation

**Example:**
```bash
curl -X POST http://localhost:8000/athletes/1/highlights \
  -F "highlight_text=Athlete focusing on marathon training - needs structured plan" \
  -F "category=training" \
  -F "source_conversation_id=123"
```

### 2. Get Athlete Highlights
**GET** `/athletes/{athlete_id}/highlights`

**Parameters:**
- `active_only` (optional): Return only active highlights (default: true)

**Example:**
```bash
curl http://localhost:8000/athletes/1/highlights?active_only=true
```

### 3. Update Highlight Status
**PUT** `/highlights/{highlight_id}`

**Parameters:**
- `is_active` (required): Set to true/false to activate/deactivate

**Example:**
```bash
curl -X PUT http://localhost:8000/highlights/1 \
  -F "is_active=false"
```

### 4. Delete Highlight
**DELETE** `/highlights/{highlight_id}`

**Example:**
```bash
curl -X DELETE http://localhost:8000/highlights/1
```

### 5. Generate Highlights from Conversation
**POST** `/athletes/{athlete_id}/highlights/generate`

**Parameters:**
- `conversation_id` (required): ID of the conversation
- `transcription` (required): The athlete's message
- `response` (required): The coach's response

**Example:**
```bash
curl -X POST http://localhost:8000/athletes/1/highlights/generate \
  -F "conversation_id=123" \
  -F "transcription=I need help with my marathon training" \
  -F "response=Let's create a structured 16-week plan focusing on gradual mileage increase"
```

## Usage Examples

### Manual Highlight Creation
```python
# Add a manual highlight
highlight_data = {
    "highlight_text": "Athlete has knee pain - recommend physio consultation",
    "category": "injury",
    "source_conversation_id": 456
}
```

### Retrieving Highlights
```python
# Get all active highlights for an athlete
highlights = get_athlete_highlights(athlete_id=1, active_only=True)

# Get all highlights including inactive ones
all_highlights = get_athlete_highlights(athlete_id=1, active_only=False)
```

### Highlight Categories
Common categories to use:
- `training`: Training-related insights
- `nutrition`: Diet and nutrition points
- `recovery`: Rest and recovery information
- `goals`: Athlete's objectives and targets
- `injury`: Injury-related notes
- `performance`: Performance observations
- `general`: General notes and reminders

## Integration with Existing Workflow

### When Saving Conversations
After saving a conversation, you can automatically generate highlights:

1. Save the conversation using `/save` endpoint
2. Use the returned conversation ID to generate highlights
3. Review and edit generated highlights as needed

### Best Practices
- Keep highlight text concise (1-2 sentences)
- Use specific categories for better organization
- Link highlights to source conversations when possible
- Regularly review and update active highlights
- Deactivate rather than delete outdated highlights

## Testing

Run the test script to verify functionality:
```bash
python test_highlights.py
```

This will:
1. Create a test athlete
2. Add sample conversations
3. Create test highlights
4. Retrieve and display highlights
5. Test status updates
6. Clean up test data

## Database Queries

### Get highlights with source conversation details
```sql
SELECT h.id, h.highlight_text, h.category, h.created_at, 
       r.transcription, r.final_response
FROM athlete_highlights h
LEFT JOIN records r ON h.source_conversation_id = r.id
WHERE h.athlete_id = ? AND h.is_active = 1
ORDER BY h.created_at DESC
```

### Count highlights by category
```sql
SELECT category, COUNT(*) as count
FROM athlete_highlights
WHERE athlete_id = ? AND is_active = 1
GROUP BY category
```

## Future Enhancements
- AI-powered highlight generation from conversations
- Highlight templates for common scenarios
- Highlight sharing between coaches
- Highlight reminders and follow-ups
- Export highlights to reports
