/**
 * LWC response wrapper for one generated exercise.
 * @author Slalom
 */
public class WorkoutExerciseDto {
    @AuraEnabled public Id exerciseId { get; set; }
    @AuraEnabled public String section { get; set; }
    @AuraEnabled public String name { get; set; }
    @AuraEnabled public Integer sets { get; set; }
    @AuraEnabled public String reps { get; set; }
}