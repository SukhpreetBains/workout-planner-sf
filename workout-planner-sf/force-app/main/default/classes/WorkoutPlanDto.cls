/**
 * LWC response wrapper for a generated workout plan.
 * @author Slalom
 */
public class WorkoutPlanDto {
    @AuraEnabled public Id planId { get; set; }
    @AuraEnabled public String goal { get; set; }
    @AuraEnabled public String experience { get; set; }
    @AuraEnabled public Integer daysPerWeek { get; set; }
    @AuraEnabled public String equipmentPreference { get; set; }
    @AuraEnabled public String planTitle { get; set; }
    @AuraEnabled public String additionalNotes { get; set; }
    @AuraEnabled public String status { get; set; }
    @AuraEnabled public List<WorkoutSessionDto> sessions { get; set; }
}