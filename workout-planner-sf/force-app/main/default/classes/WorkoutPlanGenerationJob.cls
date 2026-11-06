/**
 * Generates and stores a workout plan using the active Salesforce Prompt Builder template.
 * @author Slalom
 */
public with sharing class WorkoutPlanGenerationJob implements Queueable, Database.AllowsCallouts {
    private final Id planId;

    /**
     * @param planId The workout plan record to generate.
     */
    public WorkoutPlanGenerationJob(Id planId) {
        this.planId = planId;
    }

    /**
     * Resolves the template and saves validated session and exercise records.
     * @param context The queueable execution context.
     */
    public void execute(QueueableContext context) {
        Workout_Plan__c plan = [
            SELECT Id, Days_Per_Week__c
            FROM Workout_Plan__c
            WHERE Id = :planId
            WITH USER_MODE
            LIMIT 1
        ];

        try {
            ConnectApi.EinsteinPromptTemplateGenerationsInput input = new ConnectApi.EinsteinPromptTemplateGenerationsInput();
            input.isPreview = false;
            input.inputParams = new Map<String, ConnectApi.WrappedValue>();
            input.additionalConfig = new ConnectApi.EinsteinLlmAdditionalConfigInput();
            input.additionalConfig.applicationName = 'PromptTemplateGenerationsInvocable';

            ConnectApi.WrappedValue planReference = new ConnectApi.WrappedValue();
            planReference.value = new Map<String, String>{ 'id' => String.valueOf(plan.Id) };
            input.inputParams.put('Input:WorkoutPlan', planReference);

            ConnectApi.EinsteinPromptTemplateGenerationsRepresentation response =
                ConnectApi.EinsteinLLM.generateMessagesForPromptTemplate('Workout_Plan_Generator', input);
            if (response == null || response.generations == null || response.generations.isEmpty() ||
                String.isBlank(response.generations[0].text)) {
                throw new AuraHandledException('The prompt template returned no workout plan.');
            }

            Integer requestedDays = (Integer) plan.Days_Per_Week__c;
            WorkoutPlanJsonParser.PlanPayload generated = WorkoutPlanJsonParser.parse(
                response.generations[0].text,
                requestedDays
            );

            Savepoint savepoint = Database.setSavepoint();
            try {
                persistSessions(generated, plan.Id);
                Database.update(
                    new Workout_Plan__c(Id = plan.Id, Generation_Status__c = 'Ready'),
                    AccessLevel.USER_MODE
                );
            } catch (Exception error) {
                Database.rollback(savepoint);
                throw error;
            }
        } catch (Exception error) {
            Database.update(
                new Workout_Plan__c(Id = plan.Id, Generation_Status__c = 'Failed'),
                AccessLevel.USER_MODE
            );
        }
    }

    private static void persistSessions(WorkoutPlanJsonParser.PlanPayload generated, Id parentPlanId) {
        List<Workout_Session__c> sessions = new List<Workout_Session__c>();
        for (Integer index = 0; index < generated.sessions.size(); index++) {
            WorkoutPlanJsonParser.SessionPayload source = generated.sessions[index];
            sessions.add(new Workout_Session__c(
                Workout_Plan__c = parentPlanId,
                Session_Number__c = index + 1,
                Focus__c = source.focus
            ));
        }
        Database.insert(sessions, AccessLevel.USER_MODE);

        List<Workout_Exercise__c> exercises = new List<Workout_Exercise__c>();
        for (Integer sessionIndex = 0; sessionIndex < sessions.size(); sessionIndex++) {
            for (WorkoutPlanJsonParser.ExercisePayload source : generated.sessions[sessionIndex].exercises) {
                exercises.add(new Workout_Exercise__c(
                    Workout_Session__c = sessions[sessionIndex].Id,
                    Section__c = source.section,
                    Exercise_Name__c = source.name,
                    Sets__c = source.sets,
                    Repetitions__c = source.reps
                ));
            }
        }
        Database.insert(exercises, AccessLevel.USER_MODE);
    }
}