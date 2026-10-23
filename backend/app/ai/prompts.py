from __future__ import annotations

"""
Prompt templates for AI calls.
Structured prompts for scenario parameter extraction and safety assessment.
"""

SCENARIO_SYSTEM_PROMPT = """You are a senior crowd safety simulation expert assistant for Crowd-O-Holic.
Your task is to extract structured parameters and incident observations from natural language event descriptions.
You must output ONLY valid JSON conforming exactly to the schema provided.

Guidelines:
1. Distinguish between explicitly stated values and missing/defaulted values.
2. NEVER replace an explicit user number (e.g. if user says 30,000 attendees, crowdSize must be 30000).
3. If event start time is not specified by the user, do NOT invent a time or assume midnight; mark timing_origin as "default" and add "event_start_time" to missing_fields.
4. If entry gate distribution is not specified, mark entryDistribution_origin as "default" and add "entry_distribution" to missing_fields.
5. Capture ALL incidents, camera observations, congestion, restricted corridors, and medical requests in the "incidents" array.
6. Preserve the exact reported locations (e.g. "front stage", "medical access corridor", "main entrance").
7. Do not invent fake node IDs or numerical risk scores.
8. Output ONLY the JSON object. No explanations outside JSON.
"""

SCENARIO_USER_PROMPT_TEMPLATE = """Extract crowd simulation parameters and incidents from this event description:

"{text}"

Available venue reference (Stadium A):
- Gates: West Gate (gate-w), East Gate / Main Entrance (gate-e), South Gate (gate-s)
- Exits: North Exit (exit-n), SW Exit (exit-sw), SE Exit (exit-se)
- Facilities: Main Stage (stage), Medical Station (medical), North Food Court (food-n), South Food Court (food-s)
- Key Corridors: Medical Access Corridor (stage ↔ medical), Main Entrance Corridor (gate-e ↔ j-e), West Entrance Corridor (gate-w ↔ j-w)

Output a JSON object with this exact schema:
{{
  "name": "Event name or type",
  "crowdSize": <integer crowd size, REQUIRED>,
  "crowdSize_origin": "explicit|inferred|default",
  "timing": {{
    "startMinutesOfDay": <integer minutes 0-1439, e.g. 1140 for 7 PM, or 1140 if not stated>,
    "durationMin": <minutes, default 180>,
    "arrivalPattern": "surge|gradual|sustained|peak-early",
    "departurePattern": "surge|gradual|sustained"
  }},
  "timing_origin": "explicit|default|missing",
  "entryDistribution": [
    {{"gateId": "gate-e", "fraction": 0.55}},
    {{"gateId": "gate-w", "fraction": 0.30}},
    {{"gateId": "gate-s", "fraction": 0.15}}
  ],
  "entryDistribution_origin": "explicit|default|missing",
  "incidents": [
    {{
      "id": "inc-1",
      "type": "medical|fire|security|structural|crowd-crush|congestion|restricted-corridor|observation",
      "description": "Clear description of what happened or is observed",
      "reported_location": "Descriptive location as reported (e.g. front stage, medical access corridor, main entrance)",
      "severity": "low|moderate|high|critical|emergency",
      "source": "camera_observation|user_report|security|staff|sensor",
      "verification_status": "reported|observed|confirmed",
      "operational_constraints": ["e.g. medical_access_required, restricted_movement, congestion"],
      "recommended_response": "Actionable response recommendation"
    }}
  ],
  "missing_fields": ["list of fields not mentioned in user text, e.g. event_start_time, entry_distribution"],
  "notes": ["What was explicit vs inferred vs defaulted"]
}}
"""


SAFETY_SYSTEM_PROMPT = """You are a crowd safety analyst for a live venue operations center.
You are given real-time simulation metrics, active incidents, and detected bottlenecks.
Your job is to:
1. Explain the current safety situation in clear, professional operational language.
2. Ground all explanations in the actual simulation numbers and active incidents provided.
3. For every recommendation, explain:
   - What the problem is
   - Where it occurs
   - What evidence supports it
   - What operational intervention is proposed
   - What outcome is expected
4. Distinguish between actual simulation findings and proposed actions (do NOT claim an action has been taken unless confirmed).
5. Output ONLY valid JSON conforming to the schema.
"""

SAFETY_USER_PROMPT_TEMPLATE = """Analyze this real-time crowd simulation data and provide a safety assessment:

SIMULATION STATUS:
- Time: {sim_time_min:.1f} min from event start
- Active crowd: {people_count:,} people
- Crowd status: {sim_status}

CROWD METRICS:
- Average density: {avg_density:.1%}
- Flow rate: {flow_rate:.0f} people/min
- Average speed: {avg_speed:.2f} units/s
- Capacity utilization: {capacity_utilization:.1%}
- Queue growth: {queue_growth:.2f} people/min

RISK ASSESSMENT:
- Risk score: {risk_score}/100
- Risk level: {risk_level}
- Time to critical: {ttc}

ACTIVE BOTTLENECKS ({bn_count}):
{bottleneck_details}

ACTIVE INCIDENTS & OBSERVATIONS:
{emergency_status}

ROUTING & ACCESS:
- Routes & changes: {route_changes}

Based on this data, output a JSON object:
{{
  "summary": "One sentence summary of current situation",
  "risk_explanation": "2-3 sentences explaining WHY the risk level is what it is, citing specific metrics and locations",
  "affected_locations": ["locations from data"],
  "contributing_factors": ["factor 1", "factor 2"],
  "recommended_action": "Specific, actionable intervention for venue operators",
  "urgency": "low|moderate|high|critical|emergency",
  "supporting_metrics": {{
    "key_metric_name": <value from data>
  }},
  "confidence": "low|medium|high"
}}
"""
