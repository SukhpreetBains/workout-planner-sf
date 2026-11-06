/**
 * Creates and reads private workout plan records for the planner UI.
 * @author Slalom
 */
public with sharing class WorkoutPlanController {
    private static final Set<String> VALID_GOALS = new Set<String>{ 'Strength', 'Muscle', 'Fitness' };
    private static final Set<String> VALID_EXPERIENCE_LEVELS = new Set<String>{ 'Beginner', 'Intermediate', 'Advanced' };
    private static final Set<String> VALID_EQUIPMENT = new Set<String>{ 'Full_Gym', 'Dumbbells', 'Bodyweight_Only', 'Resistance_Bands' };

    /**
     * Creates a plan record and queues native Prompt Builder generation.
     * @param goal The selected Workout_Plan__c goal value.
     * @param experience The selected experience-level value.
     * @param daysPerWeek The requested number of weekly sessions.
     * @return The new workout plan record ID.
     */
    @AuraEnabled
    public static Id createPlan(
        String goal,
        String experience,
        Integer daysPerWeek,
        String equipmentPreference,
        String planTitle,
        String additionalNotes
    ) {
        if (!VALID_GOALS.contains(goal)) {
            throw new AuraHandledException('Choose a valid workout goal.');
        }
        if (!VALID_EXPERIENCE_LEVELS.contains(experience)) {
            throw new AuraHandledException('Choose a valid experience level.');
        }
        if (daysPerWeek == null || daysPerWeek < 1 || daysPerWeek > 7) {
            throw new AuraHandledException('Choose between 1 and 7 workout days.');
        }
        if (String.isBlank(equipmentPreference)) {
            equipmentPreference = 'Full_Gym';
        }
        if (!VALID_EQUIPMENT.contains(equipmentPreference)) {
            throw new AuraHandledException('Choose a valid equipment option.');
        }
        if (String.isBlank(planTitle)) {
            planTitle = experience + ' ' + goal + ' Plan';
        }
        if (planTitle.length() > 80) {
            throw new AuraHandledException('Plan name must be 80 characters or fewer.');
        }
        if (additionalNotes != null && additionalNotes.length() > 1000) {
            throw new AuraHandledException('Additional notes must be 1,000 characters or fewer.');
        }
        if (!Schema.sObjectType.Workout_Plan__c.isCreateable()) {
            throw new AuraHandledException('You do not have access to create workout plans.');
        }

        Workout_Plan__c plan = new Workout_Plan__c(
            Goal__c = goal,
            Experience_Level__c = experience,
            Days_Per_Week__c = daysPerWeek,
            Equipment_Preference__c = equipmentPreference,
            Plan_Title__c = planTitle.trim(),
            Additional_Notes__c = additionalNotes,
            Generation_Status__c = 'Generating'
        );
        Database.insert(plan, AccessLevel.USER_MODE);
        System.enqueueJob(new WorkoutPlanGenerationJob(plan.Id));
        return plan.Id;
    }

    /**
     * Reads a plan and its generated session and exercise records.
     * @param planId The workout plan record ID.
     * @return The plan and its child records in UI-friendly wrappers.
     */
    @AuraEnabled
    public static WorkoutPlanDto getPlan(Id planId) {
        if (planId == null) {
            throw new AuraHandledException('Workout plan was not found.');
        }

        List<Workout_Plan__c> plans = [
            SELECT Id, Goal__c, Experience_Level__c, Days_Per_Week__c, Equipment_Preference__c, Plan_Title__c, Additional_Notes__c, Generation_Status__c
            FROM Workout_Plan__c
            WHERE Id = :planId
            WITH USER_MODE
            LIMIT 1
        ];
        if (plans.isEmpty()) {
            throw new AuraHandledException('Workout plan was not found.');
        }

        Workout_Plan__c plan = plans[0];
        WorkoutPlanDto result = new WorkoutPlanDto();
        result.planId = plan.Id;
        result.goal = plan.Goal__c;
        result.experience = plan.Experience_Level__c;
        result.daysPerWeek = (Integer) plan.Days_Per_Week__c;
        result.equipmentPreference = plan.Equipment_Preference__c;
        result.planTitle = plan.Plan_Title__c;
        result.additionalNotes = plan.Additional_Notes__c;
        result.status = plan.Generation_Status__c;
        result.sessions = new List<WorkoutSessionDto>();

        List<Workout_Session__c> sessions = [
            SELECT Id, Session_Number__c, Focus__c
            FROM Workout_Session__c
            WHERE Workout_Plan__c = :planId
            WITH USER_MODE
            ORDER BY Session_Number__c
        ];
        if (sessions.isEmpty()) {
            return result;
        }

        Set<Id> sessionIds = new Map<Id, Workout_Session__c>(sessions).keySet();
        Map<Id, List<Workout_Exercise__c>> exercisesBySession = new Map<Id, List<Workout_Exercise__c>>();
        for (Workout_Exercise__c exercise : [
            SELECT Id, Workout_Session__c, Section__c, Exercise_Name__c, Sets__c, Repetitions__c
            FROM Workout_Exercise__c
            WHERE Workout_Session__c IN :sessionIds
            WITH USER_MODE
            ORDER BY Name
        ]) {
            if (!exercisesBySession.containsKey(exercise.Workout_Session__c)) {
                exercisesBySession.put(exercise.Workout_Session__c, new List<Workout_Exercise__c>());
            }
            exercisesBySession.get(exercise.Workout_Session__c).add(exercise);
        }

        for (Workout_Session__c session : sessions) {
            WorkoutSessionDto sessionDto = new WorkoutSessionDto();
            sessionDto.sessionId = session.Id;
            sessionDto.sessionNumber = (Integer) session.Session_Number__c;
            sessionDto.focus = session.Focus__c;
            sessionDto.exercises = new List<WorkoutExerciseDto>();
            List<Workout_Exercise__c> sessionExercises = exercisesBySession.get(session.Id);
            if (sessionExercises != null) {
                for (Workout_Exercise__c exercise : sessionExercises) {
                    WorkoutExerciseDto exerciseDto = new WorkoutExerciseDto();
                    exerciseDto.exerciseId = exercise.Id;
                    exerciseDto.section = exercise.Section__c;
                    exerciseDto.name = exercise.Exercise_Name__c;
                    exerciseDto.sets = (Integer) exercise.Sets__c;
                    exerciseDto.reps = exercise.Repetitions__c;
                    sessionDto.exercises.add(exerciseDto);
                }
            }
            result.sessions.add(sessionDto);
        }
        return result;
    }

}