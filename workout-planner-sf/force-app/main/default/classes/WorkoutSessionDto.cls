/**
 * LWC response wrapper for one workout session.
 * @author Slalom
 */
public class WorkoutSessionDto {
    @AuraEnabled public Id sessionId { get; set; }
    @AuraEnabled public Integer sessionNumber { get; set; }
    @AuraEnabled public String focus { get; set; }
    @AuraEnabled public List<WorkoutExerciseDto> exercises { get; set; }
}