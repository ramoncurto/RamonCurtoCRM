# Disable Automatic GPT Requests

This guide explains how to disable automatic GPT-4o-mini requests in the Elite Athlete CRM system.

## What are Automatic GPT Requests?

The system currently makes automatic GPT requests for:
- ~~Risk assessment analysis~~ (Now manual only)
- Reply suggestions
- Todo detection
- Highlights generation
- AI response generation

## Manual Risk Assessment

Risk assessment is now **manual only** by default. You can trigger it:

### In the Web Interface:
1. **Individual Athlete**: Go to athlete workspace and click "Evaluar Riesgo" button
2. **All Athletes**: Go to athletes list and click "Evaluar riesgo de todos los atletas"

### Using the Script:
```bash
python manual_risk_assessment.py
```

## How to Disable Automatic GPT

### Option 1: Using the Script (Recommended)

1. Run the provided script:
```bash
python disable_auto_gpt.py
```

2. Follow the prompts to disable automatic GPT requests

3. Restart your server:
```bash
python start_server.py
```

### Option 2: Manual Configuration

1. Create or edit the `.env` file in your project root:
```env
# Disable automatic GPT requests
AUTO_GPT_ENABLED=false

# OpenAI API Key (if you want to keep it for manual requests)
# OPENAI_API_KEY=your_openai_api_key_here
```

2. Restart your server

## What Happens When Disabled?

When `AUTO_GPT_ENABLED=false`:

- **Risk Assessment**: Manual only (no automatic assessment)
- **Reply Suggestions**: No automatic reply suggestions
- **Todo Detection**: No automatic todo creation
- **Highlights Generation**: No automatic highlights generation
- **AI Response Generation**: Manual generation still works via buttons

## Re-enabling Automatic GPT

To re-enable automatic GPT requests:

1. Set `AUTO_GPT_ENABLED=true` in your `.env` file
2. Restart your server

## Manual GPT Features Still Available

Even when automatic GPT is disabled, you can still:
- Manually generate AI responses using the "Generate Response" button
- Manually create highlights
- Manually trigger risk assessment
- Use the transcription service
- All other non-GPT features

## Benefits of Manual Risk Assessment

- **Cost Control**: Only assess when needed
- **Better Control**: Choose which athletes to assess
- **Performance**: Faster page loads
- **Privacy**: No automatic data processing

## Risk Assessment Methods

### 1. Individual Assessment
- Go to athlete workspace
- Click "Evaluar Riesgo" button
- See real-time results

### 2. Bulk Assessment
- Go to athletes list
- Click "Evaluar riesgo de todos los atletas"
- Process all athletes at once

### 3. Command Line
```bash
python manual_risk_assessment.py
```
- Interactive script
- Assess all or specific athletes
- Detailed reporting

## Troubleshooting

If you're still seeing automatic GPT requests:

1. Check that your `.env` file has `AUTO_GPT_ENABLED=false`
2. Restart your server completely
3. Clear your browser cache
4. Check the server logs for any errors

## Configuration Options

You can also set the environment variable directly:

```bash
# Windows
set AUTO_GPT_ENABLED=false

# Linux/Mac
export AUTO_GPT_ENABLED=false
```