# 1. User input

- Let users choose a goal: **get stronger, build muscle,** or **improve fitness**.
- Let users choose their experience level: **beginner, intermediate,** or **advanced**.
- Let users select how many days per week they want to work out.

# 2. AI workout plan

- Generate a simple weekly workout plan based on the user’s choices.
- For each workout, show the exercises, sets, and repetitions.
- Keep the plan easy to read and follow.
- Let users generate a different plan if they want another option.

# 3. Basic interface

- Show a short form for the user’s choices.
- Display the generated plan on the same page.
- Include a loading message while the AI creates the plan.
- Show a friendly error message if plan generation fails.

# 4. Project scope

- Use AI to generate workout plans.
- Keep the app focused on creating and viewing plans.
- Do not include accounts, payments, class bookings, or progress tracking.




# Salesforce Workout Planner

This is a Salesforce project for the Workout Planner UI. It defines a new, private Salesforce data model and uses Salesforce Prompt Builder through Apex for AI-generated plans. It does not use or change any org schema until deployed.

## Data model

- `Workout_Plan__c` stores the goal, experience level, workout days, and generation status.
- `Workout_Session__c` stores each session under its plan.
- `Workout_Exercise__c` stores exercises, sets, and repetitions under each session.
- Goal, experience, equipment, and status options are defined as restricted Salesforce picklists. The plan-day field is limited to 1 through 7 by the UI and Apex. Custom plans include a name and up to 1,000 characters of additional notes.

All three objects use private sharing. `Workout_Planner_User` grants the component's required object and field access.

## AI setup

The Apex queueable calls the `Workout_Plan_Generator` Prompt Builder template through `ConnectApi.EinsteinLLM`. The target org must support Prompt Builder / Einstein generative AI, and the running user must have permission to execute prompt templates. Generation requires the deployed template to be active. If the target org does not have these capabilities enabled, generation will show the friendly error state.

The prompt asks for a strict JSON response and the server validates the session count, exercise names, sets, and repetitions before saving the result. Credentials and model API keys are not stored in this project.

## Deploy later

From this directory, authenticate through the Salesforce browser flow and deploy the package:

```sh
sf org login web --instance-url https://login.salesforce.com --alias workout-demo
sf project deploy start --manifest manifest/package.xml --target-org workout-demo
```

For a sandbox, use `https://test.salesforce.com` or the org's My Domain URL. After deployment, assign the `Workout Planner User` permission set, confirm the prompt template is active, and add the `Workout Planner` and `Workout Planner Custom Plan` tabs to the target app's navigation.

The **Workout Planner** Lightning app has been deployed with the Workout Planner and Custom Plan tabs. Assign `Workout Planner User`, then open the app from the App Launcher.

## Experience Cloud publishing

Both planner LWCs are exposed to Experience Builder. The authenticated **Build Your Own (LWR)** site has been created and published in the connected development org. The Home route uses `workoutPlanner`; the `Create_Custom_Plan__c` route uses `createWorkoutPlan`.

Published site: [Workout Planner](https://orgfarm-466e0f8abd-dev-ed.develop.my.site.com/workoutplannervforcesite/s/). It redirects unauthenticated visitors to Salesforce login. The connected user has the `Workout_Planner_User` permission set. Users must also have permission to execute Prompt Builder templates for AI generation. Guest access is not configured because plan records use private sharing and user-mode Apex access.

## Legacy Salesforce Sites homepage

`WorkoutPlannerSite` is deployed as the Visualforce page labeled **Workout Planner Site**. Select **Workout Planner Site** in the legacy **Setup > Sites > Active Site Home Page** field. Its sample plans run in the browser and do not call Prompt Builder or save records. Use the authenticated LWC Experience Cloud site for the production AI-backed flow.

## Local checks

Run the Apex parser tests in the target org after deployment:

```sh
sf apex run test --tests WorkoutPlanJsonParserTest --target-org workout-demo --wait 10
```

The custom objects and fields are new definitions; the target org had no existing custom objects when checked. Experience Cloud Network and bundle metadata is org-specific and should be reviewed before deploying to another org.