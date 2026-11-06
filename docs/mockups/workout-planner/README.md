# Workout Planner UI Prototype

A Salesforce-inspired, standalone interface prototype for reviewing the weekly workout planning flow. It runs locally in a browser and does not require Salesforce, an account, or installed dependencies.

Open `index.html` directly to try the overview. Choose a goal and workout days, then switch between Beginner, Intermediate, and Advanced tabs. Use Create a custom plan to open `custom-plan.html` and try the additional fields. Add `?simulateError` to either page URL to preview its friendly error state.

Plan creation is simulated in the browser with sample exercise variations. This preview is not connected to an AI model, Salesforce org, or backend. The deployable Salesforce implementation is in `../../../workout-planner-sf/` and uses Prompt Builder through Apex.