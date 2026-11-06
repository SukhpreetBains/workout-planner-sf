import { LightningElement, api } from 'lwc';

const SECTION_ORDER = ['Warm-ups', 'Strength', 'Core Conditioning', 'Stretching'];

export default class WorkoutPlanResults extends LightningElement {
    @api plan;

    get sessions() {
        return (this.plan?.sessions || []).map((session) => ({
            ...session,
            sections: SECTION_ORDER.map((name) => ({
                name,
                exercises: (session.exercises || []).filter((exercise) => (exercise.section || 'Strength') === name)
            })).filter((section) => section.exercises.length)
        }));
    }
}