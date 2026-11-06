/**
 * Tests valid and invalid Prompt Builder workout plan responses.
 * @author Slalom
 */
@IsTest
private class WorkoutPlanJsonParserTest {
    /**
     * @return A valid two-session generation response.
     */
    private static String validResponse() {
        return '{"sessions":[' +
            '{"focus":"Upper body","exercises":[' +
                '{"section":"Warm-ups","name":"Arm circles","sets":1,"reps":"30 sec"},' +
                '{"section":"Strength","name":"Dumbbell press","sets":3,"reps":"8-12"},' +
                '{"section":"Strength","name":"Cable row","sets":3,"reps":"8-12"},' +
                '{"section":"Strength","name":"Lateral raise","sets":2,"reps":"10-15"},' +
                '{"section":"Core Conditioning","name":"Dead bug","sets":2,"reps":"10 each side"},' +
                '{"section":"Stretching","name":"Chest stretch","sets":1,"reps":"20-30 sec"}]},' +
            '{"focus":"Lower body","exercises":[' +
                '{"section":"Warm-ups","name":"Bodyweight squat","sets":1,"reps":"10 reps"},' +
                '{"section":"Strength","name":"Goblet squat","sets":3,"reps":"8-12"},' +
                '{"section":"Strength","name":"Hip hinge","sets":3,"reps":"8-12"},' +
                '{"section":"Strength","name":"Calf raise","sets":2,"reps":"10-15"},' +
                '{"section":"Core Conditioning","name":"Bird dog","sets":2,"reps":"8 each side"},' +
                '{"section":"Stretching","name":"Quad stretch","sets":1,"reps":"20-30 sec"}]}]}';
    }

    /**
     * Verifies the parser accepts a valid plan and strips a JSON code fence.
     */
    @IsTest
    static void parsesValidResponse() {
        WorkoutPlanJsonParser.PlanPayload plan = WorkoutPlanJsonParser.parse(
            '```json\n' + validResponse() + '\n```',
            2
        );
        Assert.areEqual(2, plan.sessions.size());
        Assert.areEqual('Warm-ups', plan.sessions[0].exercises[0].section);
        Assert.areEqual('Dumbbell press', plan.sessions[0].exercises[1].name);
        Assert.areEqual(3, plan.sessions[0].exercises[1].sets);
    }

    /**
     * Verifies each session contains all four required workout sections.
     */
    @IsTest
    static void rejectsMissingWorkoutSection() {
        Boolean didThrow = false;
        try {
            WorkoutPlanJsonParser.parse(
                validResponse().replace('"section":"Stretching"', '"section":"Strength"'),
                2
            );
        } catch (WorkoutPlanJsonParser.PlanValidationException error) {
            didThrow = true;
        }
        Assert.isTrue(didThrow, 'Expected a clear error when a workout section is missing.');
    }

    /**
     * Verifies the parser rejects a session count that differs from the request.
     */
    @IsTest
    static void rejectsWrongSessionCount() {
        Boolean didThrow = false;
        try {
            WorkoutPlanJsonParser.parse(validResponse(), 3);
        } catch (WorkoutPlanJsonParser.PlanValidationException error) {
            didThrow = true;
        }
        Assert.isTrue(didThrow, 'Expected a clear error for a mismatched session count.');
    }

    /**
     * Verifies the parser rejects malformed JSON.
     */
    @IsTest
    static void rejectsMalformedResponse() {
        Boolean didThrow = false;
        try {
            WorkoutPlanJsonParser.parse('{bad json}', 1);
        } catch (WorkoutPlanJsonParser.PlanValidationException error) {
            didThrow = true;
        }
        Assert.isTrue(didThrow, 'Expected a clear error for malformed JSON.');
    }
}