/**
 * Validates the JSON response returned by the workout plan prompt template.
 * @author Slalom
 */
public class WorkoutPlanJsonParser {
    private static final Set<String> VALID_SECTIONS = new Set<String>{
        'Warm-ups', 'Strength', 'Core Conditioning', 'Stretching'
    };

    /**
     * Parses and validates a plan response before any child records are saved.
     * @param responseText The generated JSON text.
     * @param expectedSessions The requested number of sessions.
     * @return A validated plan payload.
     */
    public static PlanPayload parse(String responseText, Integer expectedSessions) {
        if (String.isBlank(responseText) || expectedSessions == null || expectedSessions < 1 || expectedSessions > 7) {
            throw new PlanValidationException('The generated plan was incomplete.');
        }

        String normalized = responseText.trim();
        if (normalized.startsWith('```')) {
            Integer firstLineEnd = normalized.indexOf('\n');
            Integer closingFence = normalized.lastIndexOf('```');
            if (firstLineEnd < 0 || closingFence <= firstLineEnd) {
                throw new PlanValidationException('The generated plan was not valid JSON.');
            }
            normalized = normalized.substring(firstLineEnd + 1, closingFence).trim();
        }

        PlanPayload payload;
        try {
            payload = (PlanPayload) JSON.deserialize(normalized, PlanPayload.class);
        } catch (Exception error) {
            throw new PlanValidationException('The generated plan was not valid JSON.');
        }

        if (payload == null || payload.sessions == null || payload.sessions.size() != expectedSessions) {
            throw new PlanValidationException('The generated plan did not match your requested number of days.');
        }

        for (SessionPayload session : payload.sessions) {
            if (session == null || String.isBlank(session.focus) || session.focus.length() > 80 ||
                session.exercises == null || session.exercises.isEmpty() || session.exercises.size() > 11) {
                throw new PlanValidationException('The generated plan was incomplete.');
            }
            Map<String, Integer> sectionCounts = new Map<String, Integer>();
            for (String section : VALID_SECTIONS) {
                sectionCounts.put(section, 0);
            }
            for (ExercisePayload exercise : session.exercises) {
                if (exercise == null || !VALID_SECTIONS.contains(exercise.section) ||
                    String.isBlank(exercise.name) || exercise.name.length() > 120 ||
                    exercise.sets == null || exercise.sets < 1 || exercise.sets > 5 ||
                    String.isBlank(exercise.reps) || exercise.reps.length() > 20) {
                    throw new PlanValidationException('The generated plan included invalid exercise details.');
                }
                sectionCounts.put(exercise.section, sectionCounts.get(exercise.section) + 1);
            }
            if (sectionCounts.get('Warm-ups') < 1 || sectionCounts.get('Warm-ups') > 2 ||
                sectionCounts.get('Strength') < 3 || sectionCounts.get('Strength') > 5 ||
                sectionCounts.get('Core Conditioning') < 1 || sectionCounts.get('Core Conditioning') > 2 ||
                sectionCounts.get('Stretching') < 1 || sectionCounts.get('Stretching') > 2) {
                throw new PlanValidationException('The generated plan must include all four workout sections.');
            }
        }
        return payload;
    }

    public class PlanPayload {
        public List<SessionPayload> sessions;
    }

    public class SessionPayload {
        public String focus;
        public List<ExercisePayload> exercises;
    }

    public class ExercisePayload {
        public String section;
        public String name;
        public Integer sets;
        public String reps;
    }

    public class PlanValidationException extends Exception {}
}